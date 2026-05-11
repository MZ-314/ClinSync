# ClinSync
**AI-Powered Clinical Documentation & FHIR Automation System**

## Local Development

You can run the stack two ways. Pick **Option A** if you're using NeonDB and
want the simplest setup (matches the Render deployment).

### Option A — Backend only via uvicorn, Frontend via Vite (recommended)

Best for development with NeonDB. No Docker required for backend; Kafka can
be disabled (`USE_KAFKA=false`) and the pipeline runs in-process.

```bash
# 1. Backend setup
cd backend
python -m venv venv
venv\Scripts\activate         # on Windows; use `source venv/bin/activate` on macOS/Linux
pip install -r requirements.txt

# 2. Make sure your .env (in repo root) has:
#    USE_KAFKA=false
#    DATABASE_URL=postgresql+asyncpg://USER:PASS@ep-xxx-pooler.region.aws.neon.tech/DB?ssl=require
#    GROQ_API_KEY=...
#    DEEPGRAM_API_KEY=...
#    HAPI_FHIR_URL=https://hapi.fhir.org/baseR4   (or your own)

# 3. Start backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 4. In a second terminal — frontend
cd frontend
npm install
# create frontend/.env.local with: VITE_API_URL=http://127.0.0.1:8000
npm run dev
```

Open the frontend at **http://localhost:5173** and the API docs at
**http://localhost:8000/docs**.

### Option B — Full docker-compose stack (with Kafka + local Postgres + HAPI FHIR)

Best when you want the entire local infra. The frontend is **not** in compose
anymore — run it via `npm run dev` separately.

```bash
cp .env.example .env          # then fill in your API keys
docker compose up --build backend postgres kafka zookeeper hapi-fhir

# In another terminal, frontend:
cd frontend
npm install
npm run dev
```

## Services

| Service     | How it runs           | Port  | Description                     |
|-------------|------------------------|-------|---------------------------------|
| Backend API | uvicorn / Docker       | 8000  | FastAPI + LangGraph agents      |
| Frontend    | Vite dev / Vercel      | 5173  | React + Tailwind dashboard      |
| HAPI FHIR   | Docker (optional)      | 8080  | FHIR R4 server                  |
| PostgreSQL  | Docker / NeonDB        | 5432  | Relational store                |
| Kafka       | Docker (optional)      | 9092  | Event streaming (local only)    |

## Deployment

- **Backend** → Render (Docker). Set `USE_KAFKA=false`, point `DATABASE_URL`
  at NeonDB pooled endpoint with `?ssl=require`, set `CORS_ORIGINS` to your
  Vercel URL. See `backend/Dockerfile` and `.env.example`.
- **Frontend** → Vercel. Root directory: `frontend`. Set `VITE_API_URL` to
  your Render backend URL. See `frontend/README.md` and `frontend/vercel.json`.

## Project Structure

```
clinsync/
├── backend/
│   ├── app/
│   │   ├── agents/          # Person A – LangGraph agents
│   │   │   ├── transcription/
│   │   │   ├── extraction/
│   │   │   ├── coding/
│   │   │   ├── fhir_builder/
│   │   │   └── workflow/
│   │   ├── api/             # REST endpoints
│   │   ├── kafka/           # Producer / consumer
│   │   ├── models/          # SQLAlchemy models
│   │   ├── prompts/         # Person A – LLM prompt templates
│   │   ├── services/        # Business logic
│   │   └── utils/
│   └── main.py
└── frontend/
    └── src/
        ├── components/      # Person B
        ├── pages/           # Person B
        ├── services/        # Shared
        └── styles/          # Person B
```

## Tech Stack
- **Backend**: Python · FastAPI · LangGraph · LangChain · LangSmith
- **LLM**: OpenAI GPT-4o / Mistral
- **STT**: Deepgram
- **Messaging**: Apache Kafka
- **FHIR**: HAPI FHIR · fhir.resources
- **Database**: PostgreSQL / NeonDB
- **Frontend**: React · TypeScript · Vite · Tailwind CSS
- **Infra**: Docker · Kubernetes
- **Compliance**: DPDP Act 2023 · ISO 42001