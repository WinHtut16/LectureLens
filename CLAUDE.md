# CLAUDE.md

Persistent context for Claude Code. Read this at the start of every session, along with `docs/SPEC.md` and `docs/DECISIONS.md`.

## Project Context

**LectureLens** lets users search inside recordings by meaning and jump to the exact timestamp. Upload audio (or a YouTube URL) → Whisper transcribes → segments are embedded → semantic search returns timestamped results. Phase 2 adds speaker diarization so users can filter search by speaker ("find where a *student* asked about X"). This is a Master's full-stack course project AND a portfolio piece for AI/ML engineer roles.

Two non-negotiables: **(1) unit tests for every feature** (graded), **(2) a working public URL** (peer-rated on UI/UX and security). See `docs/SPEC.md` for full requirements.

The single most important architectural fact: **transcription is slow (CPU Whisper ≈ 5 min/hour of audio), so all processing runs in a background task queue. The API never blocks on it.**

## Tech Stack

- **Backend:** Python 3.11+, FastAPI, Uvicorn, Pydantic v2, SQLAlchemy 2.x, Alembic, pytest, pytest-cov, httpx, python-jose (JWT), passlib[bcrypt], slowapi.
- **Task queue:** ARQ (asyncio-native, simpler than Celery) + Redis. (See ADR-006.)
- **ML:** openai-whisper (or faster-whisper), sentence-transformers (all-MiniLM-L6-v2), FAISS (MVP) / Qdrant (stretch), pyannote.audio (Phase 2 diarization), KeyBERT (Phase 2 topics), ONNX Runtime (Phase 3).
- **Media:** yt-dlp (Phase 2 YouTube ingest), ffmpeg (audio conversion), python-magic (file validation), mutagen (audio metadata).
- **Frontend:** Next.js 14+ (App Router), React 18+, TypeScript strict, Tailwind, shadcn/ui, TanStack Query, Vitest, React Testing Library. Audio playback via the native HTML5 `<audio>` element wrapped in a custom hook.
- **Database:** PostgreSQL (Neon free tier).
- **Object storage:** Supabase Storage or Cloudflare R2.
- **Deploy:** Hugging Face Space (backend + worker), Vercel (frontend), Upstash (Redis).
- **CI:** GitHub Actions.

New dependency not listed here → propose in `DECISIONS.md` first.

## Folder Structure

```
/
├── backend/
│   ├── app/
│   │   ├── api/              # FastAPI routers, one file per resource
│   │   ├── core/             # config, security, deps
│   │   ├── db/               # SQLAlchemy models, session
│   │   ├── ml/               # transcription, diarization, embedding, search — pure-ish logic
│   │   ├── services/         # business logic (auth, recordings, search)
│   │   ├── worker/           # ARQ task definitions + the processing pipeline
│   │   └── main.py
│   ├── tests/{unit,integration}/  conftest.py
│   ├── alembic/
│   ├── pyproject.toml
│   └── Dockerfile
├── frontend/
│   ├── app/                  # Next.js routes
│   ├── components/           # one folder per component
│   ├── lib/                  # api client, hooks (incl. useAudioPlayer)
│   ├── tests/
│   └── tailwind.config.ts
├── ml/
│   ├── notebooks/            # exploration — NOT production
│   ├── scripts/              # evaluation (WER, Recall@K), ONNX export
│   └── data/                 # gitignored — local eval datasets (LibriSpeech)
├── docs/{SPEC,DECISIONS,SECURITY}.md  architecture.png
├── .github/workflows/
├── docker-compose.yml        # local: postgres + redis + minio
├── CLAUDE.md
└── README.md
```

## How to Run

```bash
# Backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
docker compose up -d postgres redis minio
alembic upgrade head
uvicorn app.main:app --reload          # API on :8000
arq app.worker.WorkerSettings          # background worker (separate terminal)

# Frontend
cd frontend && pnpm install && pnpm dev # :3000

# Tests
cd backend && pytest --cov=app --cov-report=term-missing
cd frontend && pnpm test

# Evaluation (Phase 3)
cd ml/scripts && python eval_wer.py --dataset librispeech
cd ml/scripts && python eval_search.py --queries fixtures/queries.json
```

## Coding Conventions

### Python
- Strict typing; every fn has type hints; mypy in CI.
- Pydantic v2 for all request/response models. Never accept raw `dict`/`Any` from clients.
- Service layer separation: routers parse+validate → call services → return. ORM models in `db/` only. No SQL in routers.
- ML pipeline stages live in `app/ml/` as functions taking plain inputs and returning plain outputs, so they're testable with mocks. The *orchestration* of these stages lives in `app/worker/`.
- No `print`; use the logger. async for I/O endpoints.
- Format: ruff + black, line length 100.

### TypeScript / React
- Strict mode; no `any`; no `@ts-ignore` without a reason comment.
- Server Components by default; `'use client'` only when needed (the audio player and search box need it).
- Components small (<150 lines); split otherwise.
- Tailwind utility-first; use tokens from `tailwind.config.ts`, never raw hex.
- TanStack Query for server state; polling for recording processing status.
- Naming: PascalCase components, camelCase hooks/fns, kebab-case files.

## Testing Philosophy

Write tests alongside the feature. A feature isn't done until tests pass.

- **Never load Whisper, pyannote, or the real embedder in unit tests** — too slow. Inject mocks via FastAPI dependencies / function params.
- **Deterministic targets (aim for 90%+):**
  - Chunking / segment merging logic
  - Timestamp ↔ segment-index mapping (a result must jump to the *correct* second)
  - Search ranking with fixed mock embeddings (assert order)
  - Speaker-filter logic (given labeled segments + a speaker filter, assert correct subset)
  - Input validation (bad audio MIME, oversized file, empty query, giant query)
  - Authorization (User A cannot touch User B's recordings — write this test before the route)
- **Integration tests** hit a real Postgres (docker-compose locally; GH Actions service container in CI) and a fake queue.
- **Worker pipeline** tested with all ML stages mocked, asserting status transitions queued→...→ready and failure → status=failed with error_message.

## Always Do
- Read `docs/SPEC.md` + `docs/DECISIONS.md` before a new task.
- State plan (3–6 bullets) + acceptance criteria, then write tests, then implementation.
- Keep ML stages as pure functions; keep orchestration in the worker.
- Env vars for all secrets/URLs; update `.env.example`.
- New non-trivial decision → ADR in `docs/DECISIONS.md`.
- Run the full suite before declaring done.

## Never Do
- Never block an API request on transcription/diarization — always enqueue.
- Never load real ML models in unit tests — mock them.
- Never commit secrets, real `.env`, audio files, or datasets.
- Never write raw SQL string interpolation — use SQLAlchemy.
- Never store passwords reversibly.
- Never put business logic in routers — it goes in `services/`.
- Never accept raw `dict`/`Any` from request bodies — Pydantic models only.
- Never try to identify *who* a speaker is — diarization is anonymous (Speaker 1/2) only. (Privacy, see SPEC §9.)
- Never add new tech without an ADR.
- Never disable a failing test to green CI — fix it or `xfail` with a linked issue.

## Communication Format

```
## Plan
- [bullet]
## Acceptance criteria
- [ ] tests pass
- [ ] [behavior verifiable in browser/curl]
## Files to change
- [path] — [what]
```

When unsure between two reasonable options, ask before implementing.

## Out of Scope (don't build unless asked)
Speaker identification, real-time transcription, video, non-English, TTS/audio generation, payments, social features, mobile native. See `docs/SPEC.md` §10.
