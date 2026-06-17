"""FastAPI backend for the Content Crew web app, gated behind Google sign-in.

Run with:
    uvicorn server:app --reload

Requires in .env:
    GOOGLE_CLIENT_ID
    GOOGLE_CLIENT_SECRET
    SESSION_SECRET
"""

import hashlib
import os

from authlib.integrations.starlette_client import OAuth
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from starlette.middleware.sessions import SessionMiddleware

from content_pipeline import run_with_retries, save_article

load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUTS_DIR = os.path.join(BASE_DIR, "outputs")
STATIC_DIR = os.path.join(BASE_DIR, "static")

SESSION_SECRET = os.environ.get("SESSION_SECRET")
GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET")

if not (SESSION_SECRET and GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET):
    raise RuntimeError(
        "Missing GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, or SESSION_SECRET in .env"
    )

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


def user_dir_for(email: str) -> str:
    """A filesystem-safe, per-user folder name under outputs/."""
    return hashlib.sha256(email.lower().encode()).hexdigest()[:16]


def require_user(request: Request) -> dict:
    user = request.session.get("user")
    if not user:
        raise HTTPException(status_code=401, detail="Sign in with Google to continue.")
    return user


class GenerateRequest(BaseModel):
    topic: str


@app.get("/")
def index():
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))


@app.get("/auth/login")
async def login(request: Request):
    redirect_uri = request.url_for("auth_callback")
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

    path = save_article(topic, result, subdir=user_dir_for(user["email"]))
    return {"filename": os.path.basename(path), "content": str(result)}


@app.get("/api/articles")
def list_articles(user: dict = Depends(require_user)):
    user_outputs = os.path.join(OUTPUTS_DIR, user_dir_for(user["email"]))
    if not os.path.isdir(user_outputs):
        return []
    files = sorted(os.listdir(user_outputs), reverse=True)
    return [{"filename": f} for f in files if f.endswith(".md")]


@app.get("/api/articles/{filename}")
def get_article(filename: str, user: dict = Depends(require_user)):
    safe_name = os.path.basename(filename)
    path = os.path.join(OUTPUTS_DIR, user_dir_for(user["email"]), safe_name)
    if not os.path.isfile(path):
        raise HTTPException(status_code=404, detail="Article not found.")
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    return {"filename": safe_name, "content": content}


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
