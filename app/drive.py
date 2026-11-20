import io
import json
import os
import pathlib
import re

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

from .parsing import SUPPORTED

SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]


def _service():
    raw = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")           # AWS: injected from SSM
    if raw:
        creds = service_account.Credentials.from_service_account_info(json.loads(raw), scopes=SCOPES)
    else:                                                     # local: key file path
        creds = service_account.Credentials.from_service_account_file(
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"], scopes=SCOPES)
    return build("drive", "v3", credentials=creds, cache_discovery=False)


def folder_id(link: str) -> str:
    m = re.search(r"folders/([\w-]+)", link) or re.search(r"[?&]id=([\w-]+)", link)
    return m.group(1) if m else link.strip()


def fetch_resumes(link: str, limit: int = 200) -> list[tuple[str, bytes]]:
    svc, fid = _service(), folder_id(link)
    files = svc.files().list(
        q=f"'{fid}' in parents and trashed=false", pageSize=limit,
        fields="files(id,name,mimeType)", supportsAllDrives=True,
        includeItemsFromAllDrives=True).execute()["files"]
    out = []
    for f in files:
        name, mime = f["name"], f["mimeType"]
        if mime == "application/vnd.google-apps.document":
            out.append((name + ".txt", svc.files().export_media(fileId=f["id"], mimeType="text/plain").execute()))
        elif pathlib.Path(name).suffix.lower() in SUPPORTED:
            buf = io.BytesIO()
            dl = MediaIoBaseDownload(buf, svc.files().get_media(fileId=f["id"], supportsAllDrives=True))
            done = False
            while not done:
                _, done = dl.next_chunk()
            out.append((name, buf.getvalue()))
    return out
