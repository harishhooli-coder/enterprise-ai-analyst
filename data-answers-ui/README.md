# Data-Answers UI

Next.js developer harness for manually testing the [Data-Answers Agent](../data-answers-agent/) API.

This is **not** a production business-user interface. It calls `POST /ask` and displays user-safe responses only (no SQL, table names, or schema).

## Prerequisites

- Node.js 18+
- The FastAPI backend running on port 8000 (see `../data-answers-agent/README.md`)

## Setup

```bash
cd data-answers-ui
npm install
cp .env.local.example .env.local
```

## Run

Start the API first (in another terminal):

```bash
cd ../data-answers-agent
uvicorn app.main:app --reload --port 8000
```

Then start the UI:

```bash
npm run dev
```

Open [http://localhost:3000](http://localhost:3000).

## Environment

| Variable | Description | Default |
|----------|-------------|---------|
| `NEXT_PUBLIC_API_URL` | FastAPI base URL | `http://localhost:8000` |

## CORS

The backend must allow the UI origin. Default in `data-answers-agent/.env`:

```
CORS_ORIGINS=http://localhost:3000
```

For multiple origins, use a comma-separated list.

## What you can test

- **Happy path** — grounded revenue question → answer with provenance
- **Clarification** — ambiguous revenue question → follow-up prompt
- **Declined** — out-of-scope question → routed to human
- **Policy deny** — principal with no regions → denied

The sidebar shows `/health` status and `/metrics` eval counters after each request.

## Scripts

| Command | Purpose |
|---------|---------|
| `npm run dev` | Development server on port 3000 |
| `npm run build` | Production build |
| `npm run start` | Run production build |
| `npm run lint` | ESLint |
