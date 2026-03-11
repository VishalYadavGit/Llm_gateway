# LLM Gateway (FastAPI + Multi-Tenant RAG)

Production-oriented backend service that supports:
- JWT authentication
- Multi-tenant projects
- Encrypted per-project provider API keys
- PDF ingestion + chunking + embedding + Qdrant indexing
- Unified provider adapters (OpenAI, Gemini, Claude)
- `/v1/query` with retrieval grounding + streaming support
- Redis + Dramatiq background processing

## Architecture

The codebase follows a clean modular architecture:

```text
.
├── main.py
├── core/
├── api/
├── models/
├── schemas/
├── services/
├── providers/
├── workers/
└── utils/
```

### Why this design
- `api/`: transport layer only (request/response handling).
- `services/`: business logic and orchestration.
- `providers/`: adapter pattern so each AI provider has a unified interface.
- `workers/`: asynchronous heavy tasks (PDF indexing pipeline).
- `core/`: cross-cutting concerns (config, DB, security, dependencies, middleware).

## Quick Start

1. Copy environment file:

```bash
cp .env.example .env
```

2. Start services:

```bash
docker compose up --build
```

3. Open API docs:
- http://localhost:8000/docs

## Main Endpoints

- `POST /v1/auth/register`
- `POST /v1/auth/login`
- `POST /v1/projects`
- `GET /v1/projects`
- `POST /v1/documents/upload` (multipart: `project_id`, `file`)
- `GET /v1/documents/{project_id}`
- `POST /v1/query`

## Streaming Query

`POST /v1/query` accepts `stream=true` and responds as `text/event-stream`.

## Security Notes

- API keys are encrypted at rest with Fernet.
- Project ownership is validated on every project/document/query operation.
- Retrieved context is sanitized before prompt construction to reduce prompt-injection risk.
- Rate limiting middleware throttles requests per token/IP identity.

## Worker

Dramatiq actor (`process_document`) executes:
1. PDF text extraction
2. Chunk generation
3. Embedding generation
4. Qdrant indexing
5. Metadata persistence

Run worker manually if needed:

```bash
dramatiq workers.worker_entrypoint
```
