"""FastAPI backend for the Content Crew web app, gated behind Google sign-in.

Run with:
    uvicorn server:app --reload

Requires in .env:
    GOOGLE_CLIENT_ID
    GOOGLE_CLIENT_SECRET
    SESSION_SECRET
    DATABASE_URL
"""

import os
import re
from datetime import datetime

from dotenv import load_dotenv

load_dotenv()

from authlib.integrations.starlette_client import OAuth
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from starlette.middleware.sessions import SessionMiddleware

import db
import exports
from content_pipeline import run_with_retries

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")

SESSION_SECRET = os.environ.get("SESSION_SECRET")
GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET")
DATABASE_URL = os.environ.get("DATABASE_URL")

_required = {
    "SESSION_SECRET": SESSION_SECRET,
    "GOOGLE_CLIENT_ID": GOOGLE_CLIENT_ID,
    "GOOGLE_CLIENT_SECRET": GOOGLE_CLIENT_SECRET,
    "DATABASE_URL": DATABASE_URL,
}
_missing = [name for name, value in _required.items() if not value]
if _missing:
    raise RuntimeError(f"Missing required environment variable(s): {', '.join(_missing)}")

app = FastAPI(title="Content Crew")
app.add_middleware(SessionMiddleware, secret_key=SESSION_SECRET)

oauth = OAuth()
oauth.register(
    name="google",
    client_id=GOOGLE_CLIENT_ID,
    client_secret=GOOGLE_CLIENT_SECRET,
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={"scope": "openid email profile"},
)

db.init_db()


def require_user(request: Request) -> dict:
    user = request.session.get("user")
    if not user:
        raise HTTPException(status_code=401, detail="Sign in with Google to continue.")
    return user


def make_filename(topic: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", topic.lower()).strip("-") or "untitled"
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    return f"{slug}_{timestamp}.md"


class GenerateRequest(BaseModel):
    topic: str


@app.get("/")
def index():
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))


@app.get("/auth/login")
async def login(request: Request):
    redirect_uri = str(request.url_for("auth_callback"))
    if request.headers.get("x-forwarded-proto") == "https":
        redirect_uri = redirect_uri.replace("http://", "https://", 1)
    return await oauth.google.authorize_redirect(request, redirect_uri)


@app.get("/auth/callback", name="auth_callback")
async def auth_callback(request: Request):
    token = await oauth.google.authorize_access_token(request)
    userinfo = token.get("userinfo")
    if not userinfo or not userinfo.get("email"):
        raise HTTPException(status_code=400, detail="Google did not return an email address.")
    request.session["user"] = {
        "email": userinfo["email"],
        "name": userinfo.get("name", userinfo["email"]),
        "picture": userinfo.get("picture"),
    }
    return RedirectResponse(url="/")


@app.get("/auth/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/")


@app.get("/api/me")
def me(request: Request):
    return request.session.get("user")


@app.post("/api/generate")
def generate(req: GenerateRequest, user: dict = Depends(require_user)):
    topic = req.topic.strip()
    if not topic:
        raise HTTPException(status_code=400, detail="Topic is required.")

    result = run_with_retries(topic)
    if result is None:
        raise HTTPException(
            status_code=502,
            detail="The pipeline failed after multiple retries. Check the API key and connection.",
        )

    content = str(result)
    filename = make_filename(topic)
    db.save_article(user["email"], filename, topic, content)
    return {"filename": filename, "content": content, **exports.reading_stats(content)}


@app.get("/api/articles")
def list_articles(user: dict = Depends(require_user)):
    return db.list_articles(user["email"])


@app.get("/api/articles/{filename}")
def get_article(filename: str, user: dict = Depends(require_user)):
    article = db.get_article(user["email"], filename)
    if article is None:
        raise HTTPException(status_code=404, detail="Article not found.")
    return {**article, **exports.reading_stats(article["content"])}


@app.get("/api/articles/{filename}/export")
def export_article(filename: str, format: str = "pdf", user: dict = Depends(require_user)):
    """Download an article as a PDF or Word document."""
    article = db.get_article(user["email"], filename)
    if article is None:
        raise HTTPException(status_code=404, detail="Article not found.")

    title = filename.rsplit("_", 1)[0].replace("-", " ").strip().title()
    download_base = filename[:-3] if filename.endswith(".md") else filename

    if format == "pdf":
        media_type, ext, render = "application/pdf", "pdf", exports.to_pdf
    elif format == "docx":
        media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        ext, render = "docx", exports.to_docx
    else:
        raise HTTPException(status_code=400, detail="format must be 'pdf' or 'docx'.")

    try:
        data = render(article["content"], title)
    except exports.ExportUnavailable as e:
        raise HTTPException(status_code=503, detail=str(e))

    return Response(
        content=data,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{download_base}.{ext}"'},
    )


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
