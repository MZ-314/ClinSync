# ClinSync Frontend

React 18 + Vite 6 + Tailwind 4 + shadcn/ui. Talks to the FastAPI backend
at the URL given by `VITE_API_URL`.

## Local Setup

### 1. Install dependencies

```bash
cd frontend
npm install
```

### 2. Configure environment

Create `frontend/.env.local` (gitignored) with:

```
VITE_API_URL=http://127.0.0.1:8000
```

If `VITE_API_URL` is missing the client falls back to `http://127.0.0.1:8000`,
so you only need this file if your backend runs elsewhere.

### 3. Start the dev server

```bash
npm run dev
```

The app runs on **http://localhost:5173** by default.

### 4. Make sure the backend is running

From the repo root:

```bash
# Either: run uvicorn directly (recommended for Render-style dev)
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Or: full docker-compose stack (Postgres + Kafka + HAPI FHIR + backend)
docker compose up backend postgres kafka hapi-fhir
```

If `USE_KAFKA=false` is set in your `.env`, the pipeline runs in-process and
you only need the backend service (plus a database — local Postgres or Neon).

## Build for Production

```bash
npm run build
```

Output is written to `dist/`. This is what Vercel deploys.

## Deploy to Vercel

1. Import the GitHub repo into Vercel.
2. Set **Root Directory** to `frontend`.
3. Framework Preset will auto-detect as **Vite**.
4. Add environment variable:
   - `VITE_API_URL` → your Render backend URL, e.g. `https://clinsync-backend.onrender.com`
5. Deploy.

`vercel.json` in this folder pins the build command, output dir, and adds an
SPA rewrite so client-side routes (e.g. `/transcript-review/<id>`) work on
direct page loads.

## Page → Endpoint Mapping

| Page                  | Backend endpoint(s)                                    |
|-----------------------|--------------------------------------------------------|
| `Dashboard`           | `GET /api/v1/consultations/`                           |
| `LiveConsultation`    | `POST /api/v1/consultations/`                          |
| `TranscriptReview`    | `GET /api/v1/consultations/{id}` (polled)              |
| `ClinicalEntities`    | `GET /api/v1/consultations/{id}` (polled)              |
| `MedicalCoding`       | `GET /api/v1/consultations/{id}` (polled)              |
| `FHIRViewer`          | `GET /api/v1/consultations/{id}/fhir-records`          |
| `ApprovalDashboard`   | `GET /api/v1/consultations/{id}` + `POST /api/v1/approvals/{id}` |

All API logic lives in `src/app/lib/` (`api.ts`, `hooks.ts`, `types.ts`).
