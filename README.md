---
title: Content Crew
emoji: 📝
colorFrom: purple
colorTo: pink
sdk: docker
app_port: 7860
pinned: false
---

# Content Crew

A multi-agent content pipeline — **Researcher → Writer → Editor** — built with [CrewAI](https://www.crewai.com/) and served by [Groq](https://groq.com/). Sign in with Google, type a topic, and get a researched, drafted, and edited article in a couple of minutes. Every article is saved privately to your account in Postgres.

## Features

- **Three-agent pipeline**: a researcher (with a live web search tool), a writer, and an editor run in sequence on every topic.
- **Google sign-in**: generating and viewing articles requires authentication; each user only sees their own.
- **Persistent storage**: articles are saved to a Postgres database (Neon), not local disk, so they survive restarts/redeploys.
- **Retry with backoff**: a failed LLM call is retried automatically before giving up.
- **Web UI**: a single-page app with live progress indicators while the crew works, plus a history of past articles.
- **Export & share**: copy an article to the clipboard, download it as Markdown, PDF, or Word, or publish a read-only public link anyone can open (no sign-in required) — revocable at any time.
- **Reading stats**: each article shows an estimated reading time and word count.
- **CLI mode**: run the pipeline from the terminal, including batch mode over a list of topics.

## How it works

```
                                   ┌──────────────────────┐
                                   │   Google OAuth        │
                                   └──────────▲───────────┘
                                              │ 1. sign in
                                              │
   ┌────────────────┐   4. POST /api/generate   ┌────────────────────┐
   │  User's browser │ ───────────────────────▶ │   FastAPI server    │
   │  (Web UI)        │ ◀─────────────────────── │   (server.py)        │
   └────────────────┘   6. final article         └─────────┬───────────┘
            ▲                                               │ 2. kick off crew
            │ 7. view past articles                          ▼
            │                                     ┌─────────────────────┐
            │                                     │      CrewAI Crew      │
            │                                     │  (sequential process) │
            │                                     └─────────┬───────────┘
            │                                               │
            │                     ┌─────────────────────────┼─────────────────────────┐
            │                     ▼                          ▼                          ▼
            │           ┌─────────────────┐        ┌─────────────────┐        ┌─────────────────┐
            │           │ Researcher agent │  ───▶  │  Writer agent     │  ───▶  │  Editor agent     │
            │           │ + web_search tool │        │                   │        │                   │
            │           └────────┬──────────┘        └────────┬──────────┘        └────────┬──────────┘
            │                    │                              │                              │
            │                    ▼                              ▼                              ▼
            │          ┌──────────────────┐          ┌──────────────────┐          ┌──────────────────┐
            │          │ DuckDuckGo search  │          │   Groq LLM call    │          │   Groq LLM call    │
            │          └──────────────────┘          └──────────────────┘          └──────────────────┘
            │
            │  5. save article                                                      final article
            └───────────────────────────────────┐                                          │
                                                  ▼                                          ▼
                                       ┌─────────────────────────────────────────────────────┐
                                       │              Postgres (Neon) — articles table          │
                                       │              scoped per signed-in user's email          │
                                       └─────────────────────────────────────────────────────┘
```

1. The user signs in with Google; the server stores their identity in a session cookie.
2. The user submits a topic, which kicks off the CrewAI crew.
3. The **Researcher** agent searches the web and compiles sourced findings.
4. The **Writer** agent turns those findings into a draft article.
5. The **Editor** agent polishes the draft into a final, publication-ready piece.
6. Each agent step calls Groq's LLM; the search tool calls DuckDuckGo directly.
7. The finished article is saved to Postgres, scoped to that user's email, and shown in the UI — later retrievable from "Past articles".

## Project structure

```
content_pipeline.py   # CrewAI agents/tasks/crew + CLI entry point
server.py              # FastAPI app: Google OAuth, routes, API
db.py                  # Postgres-backed article storage (incl. share tokens)
exports.py             # Reading stats + Markdown -> PDF/DOCX rendering
static/                # Frontend (HTML/CSS/JS); share.html is the public share page
test_search.py          # Standalone test for the web search tool
topics.txt              # Sample topics for CLI batch mode
Dockerfile               # Container build for deployment
```

## Running locally

1. Create a virtual environment and install dependencies:
   ```bash
   python -m venv venv
   venv\Scripts\activate        # Windows
   pip install -r requirements.txt
   ```

2. Create a `.env` file with:
   ```env
   GROQ_API_KEY=your_groq_key
   GOOGLE_CLIENT_ID=your_google_oauth_client_id
   GOOGLE_CLIENT_SECRET=your_google_oauth_client_secret
   SESSION_SECRET=any_random_string
   DATABASE_URL=your_postgres_connection_string
   ```

3. Run the web app:
   ```bash
   uvicorn server:app --reload
   ```
   Open `http://localhost:8000`.

   Or run the CLI pipeline directly:
   ```bash
   python content_pipeline.py                  # interactive, single topic
   python content_pipeline.py --batch topics.txt  # batch mode
   ```

## Environment variables

| Variable | Purpose |
|---|---|
| `GROQ_API_KEY` | LLM calls (Llama 3.1 8B Instant via Groq) |
| `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` | Google OAuth sign-in |
| `SESSION_SECRET` | Signs the session cookie |
| `DATABASE_URL` | Postgres connection string for article storage |

## Deployment

This app is built to run as a single Docker container (frontend + backend together) so there's no cross-domain cookie/session complexity. It's deployed on Hugging Face Spaces (Docker SDK), but the same `Dockerfile` works on any container host.

When deploying to a new domain, remember to add `https://<your-domain>/auth/callback` to the **Authorized redirect URIs** of your Google OAuth client in Google Cloud Console — otherwise sign-in will fail with `redirect_uri_mismatch`.

## Tech stack

CrewAI · Groq (Llama 3.1 8B Instant) · FastAPI · Authlib (Google OAuth) · PostgreSQL (Neon) · vanilla HTML/CSS/JS
