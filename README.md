

<div align="center">

# Content Crew

> Three AI agents research, write, and edit a publication-ready article on any topic, end to end.

![Python](https://img.shields.io/badge/Python-3.13-3776AB?logo=python&logoColor=white)
![CrewAI](https://img.shields.io/badge/CrewAI-multi--agent-FF5A5F)
![Groq](https://img.shields.io/badge/Groq-Llama%203.1%208B-F55036)
![FastAPI](https://img.shields.io/badge/FastAPI-server-009688?logo=fastapi&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Neon-4169E1?logo=postgresql&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-deploy-2496ED?logo=docker&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green)

</div>

Content Crew is a multi-agent content pipeline (Researcher, Writer, Editor) built with [CrewAI](https://www.crewai.com/) and served by [Groq](https://groq.com/). You sign in with Google, type a topic, and receive a researched, drafted, and edited article in a couple of minutes. Every article is saved privately to your account in Postgres.

---

## What It Does

| You do this | The system returns |
|---|---|
| Type a topic and click Generate | A researched, drafted, edited article in markdown |
| Sign in with Google | A private workspace where you see only your own articles |
| Open a past article | The full saved piece, with reading time and word count |
| Click Copy / Markdown / PDF / Word | The article on your clipboard or downloaded as a file |
| Click Share | A read-only public link anyone can open without signing in, revocable at any time |
| Run the CLI with `--batch topics.txt` | One generated article per topic in the file |

Every failed LLM call is retried automatically with exponential backoff before the pipeline gives up. Articles live in a Postgres database (Neon), so they survive restarts and redeploys.

---

## How It Works

```
            ┌─────────────────┐
            │   Google OAuth   │   (1) sign in
            └────────▲────────┘
                     │
   ┌──────────────┐  (4) POST /api/generate  ┌──────────────────┐
   │ User browser │ ───────────────────────▶ │  FastAPI server   │
   │   (Web UI)   │ ◀─────────────────────── │   (server.py)     │
   └──────────────┘  (6) final article       └────────┬─────────┘
          ▲                                            │ (2) kick off crew
          │ (7) view past articles                     ▼
          │                                  ┌────────────────────┐
          │                                  │    CrewAI Crew      │
          │                                  │ (sequential process)│
          │                                  └────────┬───────────┘
          │            ┌──────────────┬───────────────┼───────────────┐
          │            ▼              ▼                                ▼
          │     ┌────────────┐  ┌────────────┐                 ┌────────────┐
          │     │ Researcher │ ▶│   Writer   │ ──────────────▶ │   Editor   │
          │     │ + web tool │  │            │                 │            │
          │     └─────┬──────┘  └─────┬──────┘                 └─────┬──────┘
          │           ▼               ▼                              ▼
          │     ┌────────────┐  ┌────────────┐                 ┌────────────┐
          │     │ DuckDuckGo │  │  Groq LLM  │                 │  Groq LLM  │
          │     └────────────┘  └────────────┘                 └────────────┘
          │
          │ (5) save article                            final article
          └────────────────────────┐                          │
                                    ▼                          ▼
            ┌──────────────────────────────────────────────────────┐
            │      Postgres (Neon), articles table,                 │
            │      scoped per signed-in user's email                │
            └──────────────────────────────────────────────────────┘
```

1. The user signs in with Google, and the server stores their identity in a session cookie.
2. The user submits a topic, which kicks off the CrewAI crew.
3. The Researcher agent searches the web and compiles sourced findings.
4. The Writer agent turns those findings into a draft article.
5. The Editor agent polishes the draft into a final, publication-ready piece.
6. Each agent step calls Groq's LLM, and the search tool calls DuckDuckGo directly.
7. The finished article is saved to Postgres, scoped to the user's email, then shown in the UI and retrievable later from "Past articles".

---

## Tech Stack

| Tool | Role |
|---|---|
| CrewAI | Orchestrates the three-agent sequential pipeline |
| Groq (Llama 3.1 8B Instant) | Powers every agent's LLM call |
| FastAPI | Web server, routes, and API |
| Authlib | Google OAuth sign-in |
| PostgreSQL (Neon) | Persistent, per-user article storage |
| PyMuPDF / python-docx | PDF and Word export rendering |
| DuckDuckGo (ddgs) | Live web search for the Researcher agent |
| Vanilla HTML / CSS / JS | Single-page frontend |
| Docker | Single-container build for deployment |

---

## Setup

### Prerequisites

| Requirement | Notes |
|---|---|
| Python 3.13 | Runtime for the server and CLI |
| Groq API key | Create one at the Groq console |
| Google OAuth client | Client ID and secret from Google Cloud Console |
| Postgres connection string | A Neon database works well |

### Steps

1. Create a virtual environment and install dependencies:
   ```bash
   python -m venv venv
   venv\Scripts\activate        # Windows
   pip install -r requirements.txt
   ```

2. Create a `.env` file with these values:
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

4. Or run the CLI pipeline directly:
   ```bash
   python content_pipeline.py                     # interactive, single topic
   python content_pipeline.py --batch topics.txt  # batch mode
   ```

### Environment Variables

| Variable | Purpose |
|---|---|
| `GROQ_API_KEY` | LLM calls (Llama 3.1 8B Instant via Groq) |
| `GOOGLE_CLIENT_ID` | Google OAuth sign-in |
| `GOOGLE_CLIENT_SECRET` | Google OAuth sign-in |
| `SESSION_SECRET` | Signs the session cookie |
| `DATABASE_URL` | Postgres connection string for article storage |

---

## Project Structure

```
content-crew/
├── content_pipeline.py   CrewAI agents, tasks, crew, and CLI entry point
├── server.py             FastAPI app: Google OAuth, routes, API
├── db.py                 Postgres-backed article storage (incl. share tokens)
├── exports.py            Reading stats and Markdown to PDF/DOCX rendering
├── static/               Frontend (HTML/CSS/JS); share.html is the public share page
├── test_search.py        Standalone test for the web search tool
├── topics.txt            Sample topics for CLI batch mode
├── requirements.txt      Python dependencies
└── Dockerfile            Container build for deployment
```

---

## Deployment

The app runs as a single Docker container (frontend and backend together), which avoids cross-domain cookie and session complexity. It is deployed on Hugging Face Spaces (Docker SDK), and the same `Dockerfile` works on any container host.

When deploying to a new domain, add `https://<your-domain>/auth/callback` to the Authorized redirect URIs of your Google OAuth client in Google Cloud Console. Without it, sign-in fails with `redirect_uri_mismatch`.

---

## Notable Fixes and Known Limitations

| Problem | Solution |
|---|---|
| Groq (via litellm) rejected CrewAI's prompt-cache breakpoint marker | The marker is stripped before the request is sent to non-native providers |
| Windows console (cp1252) could not render CrewAI's progress emoji | stdout and stderr are reconfigured to UTF-8 at startup |
| A trailing newline pasted into a hosting secret produced an illegal Authorization header | `GROQ_API_KEY` is stripped of surrounding whitespace before use |
| PDF export occasionally produced a blank page | The PDF renderer draws text line by line with explicit positioning instead of relying on textbox overflow behavior |
| Live progress bar in the Web UI | The progress indicator is illustrative and does not stream real per-agent timing |

---

## License

Released under the MIT License.
