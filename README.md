# Recruiter Assistant (practice project)

Match a JD against a resume (score 0-100) or shortlist a whole folder (Google Drive or local).
Blind screening: names, contacts, age/gender cues are stripped before scoring. Decision support only.

## Run locally
    python3.11 -m venv .venv && source .venv/bin/activate
    pip install -r requirements.txt
    cp .env.example .env
    uvicorn app.main:app --reload        # http://localhost:8000
Try: `sample_data/jd_python_backend.txt`, source = `local:jd_python_backend`.

## Docker
    docker compose up --build

## Google Drive
Create a service account, put its key at `secrets/sa.json`, share the resume folder with its email (Viewer).

## Test
    pytest -q

## Deploy (AWS ECS Fargate)
See `guide.html` (step 8 onward) and `infra/`.
