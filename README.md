# AI Meeting Assistant 🤖

A full-stack AI-powered meeting assistant that joins Google Meet and Zoom via bot, generates real-time transcripts (Hindi/Marathi → English), extracts action items, and syncs them to Google and Outlook Calendar.

## Project Structure

```
ai-meeting-assitant/
├── client/              # Next.js 14 frontend (TypeScript + Tailwind + shadcn/ui)
├── server/              # FastAPI backend (Python 3.12)
│   ├── app/
│   │   ├── api/routes/  # REST endpoints (auth, meetings, moms, tasks...)
│   │   ├── core/        # Config, JWT, security utilities
│   │   ├── db/          # SQLAlchemy models + session
│   │   ├── services/    # Business logic (Recall.ai, Whisper, Gemini, etc.)
│   │   ├── workers/     # Celery async task workers
│   │   └── schemas/     # Pydantic request/response schemas
│   └── requirements.txt
├── docker-compose.yml   # Local dev: Postgres, Redis, API, Worker, Client
└── README.md
```

## Quick Start (Local Dev)

### 1. Configure Environment Variables

```bash
cp server/.env.example server/.env
cp client/.env.example client/.env.local
# Fill in all API keys in both files
```

**Required API Keys (server/.env):**
- `OPENAI_API_KEY` — For transcription (Whisper) and translation (GPT-4o-mini)
- `GOOGLE_AI_API_KEY` — For LLM MOM generation (Gemini 1.5 Pro)
- `RECALL_API_KEY` — For bot deployment (optional for testing)
- `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET` — For Google OAuth
- `MICROSOFT_CLIENT_ID`, `MICROSOFT_CLIENT_SECRET` — For Microsoft OAuth
- `DATABASE_URL` — PostgreSQL connection string
- `REDIS_URL` — Redis connection string

### 2. Start with Docker Compose

```bash
docker compose up --build
```

- **Frontend**: http://localhost:3000  
- **Backend API**: http://localhost:8000  
- **API Docs**: http://localhost:8000/api/docs

### 3. Run Database Migrations

```bash
docker compose exec api alembic upgrade head
```

## Manual Setup (Without Docker)

### Backend

```bash
cd server
python -m venv .venv
# Windows:
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:socket_app --reload --port 8000
```

> **Note:** the server expects a PostgreSQL instance defined by `DATABASE_URL`. If you don't have Postgres running (e.g. you skipped Docker compose) the app will log a warning and continue, but most endpoints will fail until the database is reachable. The easiest way to get a database for local testing is to run `docker compose up` or set `DATABASE_URL=sqlite+aiosqlite:///:memory:` in `.env` for a throw‑away in‑memory store.

### Frontend

```bash
cd client
npm install
npm run dev
```

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Next.js 14, TypeScript, shadcn/ui, Tailwind CSS |
| Backend | FastAPI, Celery, Socket.IO, SQLAlchemy |
| Database | PostgreSQL + pgvector, Redis |
| Meeting Bot | Recall.ai |
| Transcription | OpenAI Whisper large-v3 (OpenAI/Replicate) |
| Translation | OpenAI GPT-4o-mini |
| LLM | Google Gemini 1.5 Pro |
| Auth | OAuth2 (Google + Microsoft) + JWT |
| Calendar | Google Calendar API + Microsoft Graph API |
| Email | Resend |
| Storage | Cloudflare R2 |

## Build Order

1. **Phase 1** — Auth layer (OAuth2 + JWT)
2. **Phase 2** — Bot deployment + live transcript streaming
3. **Phase 3** — Whisper transcription + OpenAI translation
4. **Phase 4** — LLM MOM + action item extraction
5. **Phase 5** — Calendar integrations
6. **Phase 6** — Email dispatch
7. **Phase 7** — "Catch Me Up" feature
8. **Phase 8** — Dashboard polish + MOM archive
