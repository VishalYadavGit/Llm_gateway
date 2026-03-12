# LLM Gateway (FastAPI + Multi-Tenant RAG)

Production-oriented backend service that supports:
- Origin-based JWT authentication (domain validation)
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

For local development without Docker, run the API and background worker together with one command:

```bash
python main.py
```

3. Open API docs:
- http://localhost:8000/docs

## Main Endpoints

- `GET /v1/auth/token` — Request access token by origin (read from `Origin` header)
- `POST /v1/auth/register` — Admin account registration
- `POST /v1/auth/login` — Admin login
- `POST /v1/projects`
- `GET /v1/projects`
- `POST /v1/documents/upload` (multipart: `project_id`, `file`)
- `GET /v1/documents/{project_id}`
- `POST /v1/query`

## Integration Flow

1. Admin user creates an account and logs into the admin panel.
2. Admin creates a project, sets `allowed_origin`, and uploads documents.
3. End-user website calls `GET /v1/auth/token` on each page load.
4. API validates request `Origin` against `allowed_origin` and returns a short-lived token.
5. Website sends `POST /v1/query` with `Authorization: Bearer <token>` and query payload.
6. API resolves project from token and returns the model response.

## Streaming Query

`POST /v1/query` accepts `stream=true` and responds as `text/event-stream`.

## Security Notes

- **Authentication**: Origins (domains) must be pre-registered in the system. Send `GET /v1/auth/token` — no body needed. The server reads the `Origin` header automatically and returns a 15-minute access token if the origin is registered.
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
