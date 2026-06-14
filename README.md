# LectureLens 🎧🔍

> Search inside your recordings by meaning. Jump to the exact moment someone said what you're looking for.

[![CI](https://img.shields.io/badge/CI-pending-lightgrey)](#) [![Coverage](https://img.shields.io/badge/coverage-pending-lightgrey)](#) [![Live Demo](https://img.shields.io/badge/demo-coming%20soon-lightgrey)](#)

**Live demo:** [coming soon] · **Docs:** [`docs/`](./docs)

---

## What it does

Upload a lecture, meeting, or podcast (or paste a YouTube link). LectureLens transcribes it, then lets you **search by meaning** — not just keywords — and jump straight to the timestamp.

Type *"where did a student ask about overfitting?"* and land at 47:23, in that student's turn. It works because the app combines two capabilities most people don't know exist:

- **Semantic search over audio** — "gradient descent" matches a segment that says "how the model reduces its error," even without those words.
- **Speaker diarization** — the app figures out *who spoke when*, so you can filter search to one speaker (a student vs. the professor).

## Why this exists

Recorded lectures are functionally unsearchable — you scrub a two-hour timeline guessing. Tools like Otter do keyword search; none combine *semantic* search with *speaker-filtered* search in a free, self-hostable tool. LectureLens is that tool, and a demonstration of an end-to-end ML system: ASR, diarization, embedding, retrieval, evaluation, and CPU-optimized deployment.

## How it works

```
Upload audio / YouTube URL
        │  (enqueued — API never blocks)
        ▼
┌──────────────────────── background worker (ARQ) ───────────────────────┐
│  1. yt-dlp (if YouTube) → audio                                        │
│  2. Whisper → timestamped transcript segments                          │
│  3. pyannote → "who spoke when" (Speaker 1/2), mapped onto segments    │
│  4. merge into ~30s windows → sentence-transformer embeddings          │
│  5. index in FAISS with metadata {recording, speaker, start_seconds}   │
│  6. KeyBERT topics + summary                                           │
│  status: queued → transcribing → diarizing → embedding → ready         │
└────────────────────────────────────────────────────────────────────────┘
        ▼
Search "where did a student ask about X" (filter: Student)
        ▼
Ranked, timestamped results → click → audio player jumps to the moment
```

## Architecture

```
┌──────────────────────────────────────────────┐
│  Next.js Frontend (Vercel)                    │
│  Upload · Recording list · Transcript +       │
│  audio player · Semantic search · Speaker     │
│  filter · Summaries                           │
└───────────────┬──────────────────────────────┘
                │ JSON / HTTPS
                ▼
┌──────────────────────────────────────────────┐
│  FastAPI (Hugging Face Space, CPU)            │
│  /auth /recordings /search /health            │
└──────┬─────────────────┬──────────────┬───────┘
       │                 │              │
       ▼                 ▼              ▼
┌────────────┐   ┌───────────────┐  ┌──────────────────┐
│ Postgres   │   │ Redis (queue) │  │ FAISS (in-memory │
│ (Neon)     │   │ (Upstash)     │  │ segment vectors) │
└────────────┘   └───────┬───────┘  └──────────────────┘
                         ▼
              ┌────────────────────────┐
              │ ARQ worker:            │
              │ Whisper · pyannote ·   │
              │ embeddings · KeyBERT   │
              └────────────────────────┘
       ┌────────────────────────────────────┐
       │ Object storage (Supabase / R2):    │
       │ audio files                        │
       └────────────────────────────────────┘
```

## Tech stack

| Layer | Tech |
|---|---|
| Frontend | Next.js 14 · TypeScript · Tailwind · shadcn/ui · TanStack Query · HTML5 audio |
| Backend | FastAPI · Pydantic v2 · SQLAlchemy · Alembic · slowapi |
| Queue | ARQ · Redis |
| ML | Whisper (faster-whisper) · sentence-transformers · FAISS · pyannote.audio · KeyBERT · ONNX Runtime |
| Media | yt-dlp · ffmpeg · python-magic |
| Data | PostgreSQL · Supabase Storage |
| Deploy | Hugging Face Spaces · Vercel · Upstash · GitHub Actions |
| Tests | pytest · Vitest · React Testing Library |

## Datasets (for evaluation only — users supply their own audio)

| Dataset | Use | Source |
|---|---|---|
| LibriSpeech (test-clean) | Word Error Rate of transcription | https://www.openslr.org/12 |
| Held-out query set (self-authored) | Search Recall@K / MRR | `ml/scripts/fixtures/queries.json` |

No corpus download is needed to run the app — recordings come from user uploads or YouTube.

## Metrics

(Filled in as the project progresses — these are the headline numbers.)

| Metric | Value |
|---|---|
| Word Error Rate (LibriSpeech test-clean, Whisper base) | — |
| Search Recall@5 / MRR (held-out queries) | — |
| Transcription throughput (min audio / min compute, CPU) | — |
| Search latency p50 / p95 | — |
| Embedding latency before/after ONNX INT8 | — |

## Quick start

### Prerequisites
- Python 3.11+, Node 20+, ffmpeg, Docker, pnpm
- A HuggingFace token (pyannote models are gated — accept their terms)

### Setup
```bash
git clone https://github.com/[you]/lecturelens.git
cd lecturelens

# Backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env          # set DB url, JWT secret, HF token, storage keys
docker compose up -d postgres redis minio
alembic upgrade head
uvicorn app.main:app --reload         # API :8000
arq app.worker.WorkerSettings         # worker (new terminal)

# Frontend (new terminal)
cd frontend
pnpm install
cp .env.example .env.local
pnpm dev                              # :3000
```

### Run tests
```bash
cd backend && pytest --cov=app --cov-report=term-missing
cd frontend && pnpm test
```

## Project structure
```
backend/   FastAPI API + ARQ worker + ML pipeline
frontend/  Next.js app
ml/        notebooks, evaluation scripts (WER, Recall@K), ONNX export
docs/      SPEC.md, DECISIONS.md, SECURITY.md, architecture.png
.github/   CI workflows
```
See `CLAUDE.md` for conventions and `docs/SPEC.md` for the full specification.

## Testing
- Backend unit tests mock Whisper/pyannote/embedder and cover the bug-prone logic: chunking, **timestamp↔segment mapping** (a wrong mapping sends users to the wrong moment), ranking, speaker filtering, validation, and authorization. Integration tests hit a real Postgres.
- Worker pipeline tested via mocked stages asserting status transitions and failure handling.
- Frontend tests cover the search box, transcript view, audio player controls, recording list, and auth.
- Coverage gates: 70% overall, 90% on `app/services` and `app/api`.

## Security
See [`docs/SECURITY.md`](./docs/SECURITY.md). Audio is treated as high-sensitivity. Highlights: bcrypt passwords; JWT access+refresh; per-user authorization on every recording route (no IDOR); audio validated by magic bytes with size/duration caps; SSRF guard on YouTube URLs; rate limiting; secrets in env vars. Diarization is **anonymous** (Speaker 1/2) — the app never identifies who a person is.

## Roadmap
- [ ] **Phase 1 (MVP):** auth, audio upload, async Whisper transcription, transcript + audio player, semantic search, jump-to-timestamp
- [ ] **Phase 2:** speaker diarization, speaker-filtered search, speaker rename, YouTube ingestion, auto-summary + topics
- [ ] **Phase 3:** cross-recording search, evaluation pipeline (WER + Recall@K), ONNX INT8 optimization, FAISS→Qdrant
- [ ] Public live demo with a pre-indexed sample talk

## License
[MIT recommended for a portfolio project.]

## Acknowledgments
OpenAI Whisper · pyannote.audio · sentence-transformers · FAISS · LibriSpeech · yt-dlp
