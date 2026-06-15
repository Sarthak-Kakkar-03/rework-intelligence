# Rework Autopsy

Prototype for analyzing AI-assisted PRs and the downstream rework they create.

The goal is to show where agent-written work is causing human follow-up, classify the likely reason, and point to the context source that may need review.

## Structure

```text
backend/                 Python backend scaffold
frontend-rework-autopsy/ Next.js frontend scaffold
```

## Frontend

```bash
cd frontend-rework-autopsy
npm install
npm run dev
```

Useful scripts:

```bash
npm run lint
npm run format
npm run format:check
npm run build
```

## Backend

```bash
cd backend
python main.py
```

The backend is currently an initialization scaffold. Planned work includes FastAPI endpoints, Pydantic models, local JSON data loading, and a rule-based rework classifier.

## MVP Direction

- Local synthetic PR/review/rework data
- Rule-based classification of rework causes
- Dashboard for top context gaps and estimated rework hours
- Detail view with evidence and suggested context source to review

See [Mock Data Notes](docs/mock-data.md) for the synthetic data shape and classification taxonomy.
