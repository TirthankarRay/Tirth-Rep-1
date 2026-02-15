# SCLC Patient Journey Dashboard - US Market

Interactive analytics dashboard tracking Small Cell Lung Cancer (SCLC) patient journeys across the US healthcare system.

## Project Structure

```
├── backend/          # FastAPI Python backend
│   ├── app/
│   │   ├── api/      # API route handlers
│   │   ├── models/   # SQLAlchemy ORM models
│   │   ├── schemas/  # Pydantic validation schemas
│   │   ├── services/ # Business logic
│   │   └── db/       # Database configuration
│   ├── migrations/   # Alembic migrations
│   └── tests/        # Backend tests
├── frontend/         # React + TypeScript frontend
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   ├── hooks/
│   │   ├── services/
│   │   └── types/
│   └── tests/
└── docker-compose.yml
```

## Quick Start

```bash
# Start all services
docker-compose up -d

# Backend only
cd backend && pip install -r requirements.txt && uvicorn app.main:app --reload

# Frontend only
cd frontend && npm install && npm run dev
```

## Tech Stack

- **Frontend**: React 18, TypeScript, Vite, Tailwind CSS, Recharts, D3.js
- **Backend**: Python 3.11, FastAPI, SQLAlchemy 2.0, Pydantic v2
- **Database**: PostgreSQL 15 + TimescaleDB
