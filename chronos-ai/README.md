# Chronos AI — Universal Calendar Event Generator

Convert arbitrary text (emails, invites, schedules, syllabi, deadlines, itineraries,
notes) into accurate, downloadable **iCalendar (`.ics`)** files.

- **Python** backend, **gRPC + Protocol Buffers** for internal service communication,
  **Qwen** as the primary LLM (OpenAI-compatible server, e.g. vLLM).
- Multi-event extraction, deterministic date/time + timezone handling, independent
  validation, clarification questions, reminders (VALARM), recurrence (RRULE), and a
  parse-after-generate semantic check.
- Runs out of the box in **mock mode** (deterministic, no Qwen credentials) and
  upgrades to a real Qwen server by changing environment variables.

> **The LLM never writes ICS.** It returns structured event data that is validated
> independently; deterministic Python builds and validates the calendar.

## Architecture

```
Next.js frontend ──HTTPS/REST──> FastAPI gateway ──gRPC──> services:
  input_processing · ai_extraction (Qwen/mock) · date_normalization ·
  event_validation · clarification · reminder · ics_generation ·
  ics_validation · artifact
```

For the MVP all gRPC services run in **one server process** (one container), but each
has a real, separately-defined Protobuf contract and servicer, so services can be
split into their own deployments later with no code change beyond target env vars.

See [`docs/architecture.md`](docs/architecture.md), [`docs/grpc-contracts.md`](docs/grpc-contracts.md),
[`docs/api.md`](docs/api.md), [`docs/ics-format.md`](docs/ics-format.md),
[`docs/security.md`](docs/security.md), [`docs/testing.md`](docs/testing.md).

## Requirements

- Python 3.11+ (3.12 recommended)
- Node.js 20+
- Docker + Docker Compose (optional, for the one-command run)

## Quick start (Docker Compose)

```bash
cd chronos-ai
docker compose up --build
# frontend: http://localhost:3000
# gateway:  http://localhost:8000  (OpenAPI docs at /docs)
```

This runs in **mock mode** by default — no Qwen credentials needed.

## Quick start (local, no Docker)

### 1. Backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Generate gRPC stubs from the .proto files (REQUIRED before running/testing):
python scripts/gen_proto.py

cp .env.example .env            # defaults to mock mode

# Terminal A — gRPC services:
python -m app.grpc_servers.server

# Terminal B — FastAPI gateway:
uvicorn app.main:app --reload --port 8000
```

### 2. Frontend

```bash
cd frontend
npm install
cp .env.local.example .env.local
npm run dev        # http://localhost:3000
```

## Using a real Qwen model (vLLM)

Serve Qwen with an OpenAI-compatible endpoint (vLLM supports guided JSON + LoRA):

```bash
vllm serve Qwen/Qwen2.5-14B-Instruct --enable-lora   # optionally --lora-modules ...
```

Set `backend/.env`:

```ini
QWEN_PROVIDER=openai_compatible
QWEN_API_BASE_URL=http://localhost:8001/v1
QWEN_API_KEY=EMPTY
QWEN_MODEL=Qwen/Qwen2.5-14B-Instruct   # or your registered LoRA adapter name
```

The extraction adapter asks the server for **schema-constrained JSON** (vLLM
`guided_json`), disables Qwen "thinking", and validates every field independently.
If the model fails, the request errors clearly — it never fabricates success.

## Environment variables

See [`backend/.env.example`](backend/.env.example). Key ones:

| Variable | Purpose |
|---|---|
| `QWEN_PROVIDER` | `mock` (default) or `openai_compatible` |
| `QWEN_API_BASE_URL`, `QWEN_API_KEY`, `QWEN_MODEL` | Qwen server config |
| `DEFAULT_TIMEZONE` | Fallback IANA tz for relative dates |
| `GRPC_*_TARGET` | Internal gRPC targets (point at `grpc:50051` in compose) |
| `ARTIFACT_STORAGE_PATH`, `ARTIFACT_TTL_SECONDS` | Temp artifact storage |

## Running tests

```bash
cd backend
python scripts/gen_proto.py      # stubs needed for gRPC + API tests
pytest
```

- The suite runs in **mock mode** and needs **no Qwen key**.
- `test_grpc.py` and `test_api.py` `importorskip` the generated stubs, so if you skip
  `gen_proto.py` they are skipped rather than failing.
- Tests assert the **actual contents** of generated calendars (local times, exclusive
  all-day end dates, VALARM counts, RRULE), not just that a file was produced.

## Frontend production build

```bash
cd frontend
npm run build && npm start
```

## Troubleshooting

- **`ModuleNotFoundError: app.grpc_gen...`** — run `python scripts/gen_proto.py`.
- **Gateway `/api/v1/ready` returns `degraded`** — the gRPC server isn't running/reachable.
- **PDF/DOCX upload errors** — ensure `pymupdf` / `python-docx` installed (in requirements).

## Known limitations

See the "Known limitations" section at the end of this README's companion in
[`docs/testing.md`](docs/testing.md) and the project summary. In brief: Postgres/Redis/
Celery and auth are scaffolded as roadmap (the MVP is stateless with temp artifacts);
the mock provider is heuristic (real extraction quality comes from Qwen); OCR and
CSV/XLSX are not implemented in this slice.
