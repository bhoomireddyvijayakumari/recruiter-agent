import os
import pathlib

from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, File, Form, HTTPException, UploadFile  # noqa: E402
from fastapi.staticfiles import StaticFiles  # noqa: E402

from . import drive  # noqa: E402
from .anonymize import jd_warnings  # noqa: E402
from .parsing import SUPPORTED, extract_text  # noqa: E402
from .scoring import rank  # noqa: E402

NOTE = ("Decision support only. Scores use anonymized text (no name, contact, age, gender, photo, "
        "address). A human must make every hiring decision.")
ROOT = pathlib.Path(os.getenv("RESUME_ROOT", "./resumes")).resolve()
app = FastAPI(title="Recruiter Assistant")


def read_jd(text: str, f: UploadFile | None) -> str:
    jd = extract_text(f.filename, f.file.read()) if f and f.filename else (text or "")
    if len(jd.split()) < 20:
        raise HTTPException(400, "Please provide a job description (pasted text or a file).")
    return jd


def local_files(sub: str):
    p = (ROOT / sub).resolve()
    if p != ROOT and ROOT not in p.parents:
        raise HTTPException(400, "Path is outside RESUME_ROOT.")
    if not p.is_dir():
        raise HTTPException(404, f"Folder not found: {sub}")
    return [(f.name, f.read_bytes()) for f in sorted(p.iterdir()) if f.suffix.lower() in SUPPORTED]


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/api/match")
def match(jd_text: str = Form(""), jd_file: UploadFile | None = File(None), resume: UploadFile = File(...)):
    jd = read_jd(jd_text, jd_file)
    res = rank(jd, [(resume.filename, extract_text(resume.filename, resume.file.read()))])
    return {"result": res["ranked"][0] if res["ranked"] else None, "skipped": res["skipped"],
            "jd_warnings": jd_warnings(jd), "note": NOTE}


@app.post("/api/shortlist")
def shortlist(jd_text: str = Form(""), jd_file: UploadFile | None = File(None),
              source: str = Form(...), top_n: int = Form(10), min_score: float = Form(0)):
    jd = read_jd(jd_text, jd_file)
    try:
        files = local_files(source[6:]) if source.startswith("local:") else drive.fetch_resumes(source)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(502, f"Could not read resumes: {e}")
    if not files:
        raise HTTPException(404, "No PDF/DOCX/TXT resumes found in that location.")
    res = rank(jd, [(n, extract_text(n, d)) for n, d in files])
    ranked = [r for r in res["ranked"] if r["score"] >= min_score][:top_n]
    return {"total": len(files), "shortlist": ranked, "skipped": res["skipped"],
            "jd_warnings": jd_warnings(jd), "note": NOTE}


app.mount("/", StaticFiles(directory=pathlib.Path(__file__).parent / "static", html=True), name="ui")
