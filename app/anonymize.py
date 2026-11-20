"""Blind screening: remove identity and protected-attribute signals BEFORE any scoring."""
import re

LABEL_LINES = re.compile(
    r"(?im)^\s*(date of birth|dob|d\.o\.b|age|gender|sex|marital status|nationality|religion|"
    r"caste|father.s name|mother.s name|passport( no)?|address|hobbies)\s*[:\-].*$"
)
PATTERNS = [
    (re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+"), " "),                                   # emails
    (re.compile(r"https?://\S+|www\.\S+|(linkedin|github)\.com/\S+", re.I), " "),     # links
    (re.compile(r"\+?\d[\d\s().-]{8,}\d"), " "),                                       # phones
    (re.compile(r"\b(he|she|him|her|his|hers|mr|mrs|ms|miss)\b\.?", re.I), " "),      # pronouns/titles
    (re.compile(r"\b(male|female|married|single|unmarried)\b", re.I), " "),
    (re.compile(r"\b(19|20)\d{2}\b"), " "),   # years: graduation year is an age proxy
]
BIASED_JD = re.compile(
    r"\b(young|youthful|digital native|recent graduate|fresh graduate|native speaker|"
    r"male|female|man|woman|married|single|unmarried|age limit|under \d{2}|"
    r"christian|hindu|muslim|healthy|able-bodied)\b", re.I)


def anonymize(text: str) -> str:
    lines = text.splitlines()
    for i, line in enumerate(lines):          # first non-empty line is usually the candidate's name
        if line.strip():
            lines[i] = ""
            break
    text = LABEL_LINES.sub("", "\n".join(lines))
    for pat, repl in PATTERNS:
        text = pat.sub(repl, text)
    return re.sub(r"[ \t]+", " ", text).strip()


def jd_warnings(jd: str) -> list[str]:
    """Flag wording in the JD that could itself be discriminatory."""
    return sorted({m.group(0).lower() for m in BIASED_JD.finditer(jd)})
