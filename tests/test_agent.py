from app.anonymize import anonymize, jd_warnings
from app.scoring import rank

JD = """Backend Engineer
- Build REST API services in Python and FastAPI
- Deploy containers with Docker on AWS
- Design PostgreSQL schemas and write SQL
- Write automated tests and work in an agile team"""


def test_anonymize_removes_identity_signals():
    out = anonymize("John Smith\nEmail: j@x.com\nDOB: 01/01/1990\nGender: Male\nPython developer, born 1990")
    for bad in ("John", "j@x.com", "1990", "Male"):
        assert bad not in out
    assert "Python" in out


def test_jd_bias_warning():
    assert "young" in jd_warnings("We want a young, dynamic engineer")


def test_relevant_resume_ranks_first():
    good = "A B\nBuilt REST API services with Python and FastAPI, Docker containers on AWS, PostgreSQL SQL schemas, automated testing in agile teams."
    bad = "C D\nRetail store manager handling inventory, staff rosters, customer service and visual merchandising for a clothing chain."
    out = rank(JD, [("bad.txt", bad), ("good.txt", good)])["ranked"]
    assert out[0]["file"] == "good.txt" and out[0]["score"] > out[1]["score"]
