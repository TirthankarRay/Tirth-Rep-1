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
├── minutes/          # Meeting transcription service
│   ├── Dockerfile    # Multi-stage: MCP server + CLI
│   ├── config.toml   # Configuration template
│   └── setup.sh      # Local installation script
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

## Minutes — Meeting Transcription Service

Integrated deployment of [silverstein/minutes](https://github.com/silverstein/minutes), a local-first meeting transcription and memory system with MCP server support.

```bash
# Run via Docker
docker compose up minutes-mcp minutes-watcher

# Or install locally
./minutes/setup.sh
```

- **MCP Server**: Available on port `3100` for Claude Desktop, Claude Code, and other MCP-compatible agents
- **File Watcher**: Auto-processes voice memos dropped into the inbox directory
- **CI/CD**: Container images built and published to GHCR on push

See [PR #1](https://github.com/TirthankarRay/Tirth-Rep-1/pull/1) for full details.

## Tech Stack

- **Frontend**: React 18, TypeScript, Vite, Tailwind CSS, Recharts, D3.js
- **Backend**: Python 3.11, FastAPI, SQLAlchemy 2.0, Pydantic v2
- **Database**: PostgreSQL 15 + TimescaleDB
- **Meeting Intelligence**: [Minutes](https://github.com/silverstein/minutes) (Rust CLI + Node MCP server)
