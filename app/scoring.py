"""RAG-style scoring: embed resume chunks into a vector DB, retrieve the best chunk per JD requirement."""
import os
import re
import uuid

import chromadb
from fastembed import TextEmbedding

from .anonymize import anonymize

W_SEM, W_SKILL = 0.6, 0.4          # score = 100 * (0.6*semantic + 0.4*skill coverage)
SIM_LOW, SIM_HIGH = 0.45, 0.85     # cosine range stretched to 0..1 (tune on your own data)
SKILLS = {
    "python", "java", "javascript", "typescript", "c++", "c#", "golang", "rust", "sql", "nosql",
    "postgresql", "mysql", "mongodb", "redis", "aws", "azure", "gcp", "docker", "kubernetes",
    "terraform", "ci/cd", "jenkins", "git", "linux", "react", "angular", "vue", "node.js", "django",
    "flask", "fastapi", "spring", "rest api", "graphql", "microservices", "kafka", "spark", "hadoop",
    "airflow", "pandas", "numpy", "scikit-learn", "tensorflow", "pytorch", "machine learning",
    "deep learning", "nlp", "computer vision", "llm", "rag", "data analysis", "tableau", "power bi",
    "excel", "etl", "agile", "scrum", "jira", "selenium", "testing", "devops", "mlops", "security",
    "communication", "leadership", "project management", "salesforce", "sap", "seo", "figma",
}
_model = None


def _embed(texts):
    global _model
    if _model is None:
        _model = TextEmbedding(os.getenv("EMBED_MODEL", "BAAI/bge-small-en-v1.5"))
    return [v.tolist() for v in _model.embed(texts)]


def chunk(text: str, size: int = 60, overlap: int = 15):
    words = text.split()
    chunks = [" ".join(words[i:i + size]) for i in range(0, len(words), size - overlap)]
    return [c for c in chunks if len(c.split()) >= 5]


def requirements(jd: str):
    lines = [re.sub(r"^[\s\-•*\d.)]+", "", l).strip() for l in jd.splitlines()]
    reqs = [l for l in lines if len(l.split()) >= 5]
    return (reqs or chunk(jd, 30))[:25]


def _has(term: str, text: str) -> bool:
    return re.search(rf"(?<![\w+#]){re.escape(term)}(?![\w+#])", text, re.I) is not None


def rank(jd: str, resumes: list[tuple[str, str]]) -> dict:
    """resumes = [(filename, raw_text)]. Returns {'ranked': [...], 'skipped': [...]}."""
    reqs, skills = requirements(jd), sorted(s for s in SKILLS if _has(s, jd))
    req_vecs = _embed(reqs)
    col = chromadb.EphemeralClient().create_collection(
        f"r{uuid.uuid4().hex}", metadata={"hnsw:space": "cosine"})
    clean, skipped = {}, []
    for i, (name, raw) in enumerate(resumes):
        text = anonymize(raw)
        chunks = chunk(text)
        if not chunks:
            skipped.append(f"{name} (no extractable text - scanned PDF?)")
            continue
        clean[i] = (name, text)
        col.add(ids=[f"{i}-{j}" for j in range(len(chunks))], documents=chunks,
                embeddings=_embed(chunks), metadatas=[{"rid": i} for _ in chunks])
    ranked = []
    for i, (name, text) in clean.items():
        res = col.query(query_embeddings=req_vecs, n_results=1, where={"rid": i})
        sims = [1 - d[0] for d in res["distances"]]
        sem = sum(min(max((s - SIM_LOW) / (SIM_HIGH - SIM_LOW), 0), 1) for s in sims) / len(sims)
        matched = [s for s in skills if _has(s, text)]
        cov = len(matched) / len(skills) if skills else None
        score = 100 * (W_SEM * sem + W_SKILL * cov) if cov is not None else 100 * sem
        best = sorted(range(len(sims)), key=lambda k: -sims[k])[:2]
        ranked.append({
            "file": name, "score": round(score, 1), "semantic": round(sem, 2),
            "skill_coverage": None if cov is None else round(cov, 2),
            "matched_skills": matched, "missing_skills": [s for s in skills if s not in matched],
            "evidence": [{"requirement": reqs[k], "resume_excerpt": res["documents"][k][0][:240],
                          "similarity": round(sims[k], 2)} for k in best],
            "why": (f"Matched {len(matched)}/{len(skills)} named skills; " if skills else "") +
                   f"average alignment with JD requirements {sem:.0%}.",
        })
    ranked.sort(key=lambda r: -r["score"])
    return {"ranked": ranked, "skipped": skipped}
