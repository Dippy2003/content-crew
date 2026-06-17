"""FastAPI backend for the Content Crew web app.

Run with:
    uvicorn server:app --reload
"""

import os

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from content_pipeline import run_with_retries, save_article

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUTS_DIR = os.path.join(BASE_DIR, "outputs")
STATIC_DIR = os.path.join(BASE_DIR, "static")

app = FastAPI(title="Content Crew")


class GenerateRequest(BaseModel):
    topic: str


@app.get("/")
def index():
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))


@app.post("/api/generate")
def generate(req: GenerateRequest):
    topic = req.topic.strip()
    if not topic:
        raise HTTPException(status_code=400, detail="Topic is required.")

    result = run_with_retries(topic)
    if result is None:
        raise HTTPException(
            status_code=502,
            detail="The pipeline failed after multiple retries. Check the API key and connection.",
        )

    path = save_article(topic, result)
    return {"filename": os.path.basename(path), "content": str(result)}


@app.get("/api/articles")
def list_articles():
    if not os.path.isdir(OUTPUTS_DIR):
        return []
    files = sorted(os.listdir(OUTPUTS_DIR), reverse=True)
    return [{"filename": f} for f in files if f.endswith(".md")]


@app.get("/api/articles/{filename}")
def get_article(filename: str):
    safe_name = os.path.basename(filename)
    path = os.path.join(OUTPUTS_DIR, safe_name)
    if not os.path.isfile(path):
        raise HTTPException(status_code=404, detail="Article not found.")
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    return {"filename": safe_name, "content": content}


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
