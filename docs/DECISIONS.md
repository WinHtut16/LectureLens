# DECISIONS.md

Architecture Decision Records (ADRs). Every non-trivial choice gets an entry: Context → Decision → Consequences. Append new entries; never edit historical ones (supersede with a new ADR).

---

## ADR-001: Build a semantic audio search tool with speaker-aware search

**Date:** [today]
**Status:** Accepted

### Context
Master's full-stack course project doubling as an AI/ML portfolio piece. Must be (1) full-stack, (2) deployable to a public URL, (3) unit-tested, (4) peer-rated on UI/UX and security. The owner wants a project whose novelty comes from packaging a little-known AI capability accessibly — not from inventing new AI. A prior course (same professor) used the MIND news dataset + collaborative filtering, so this must be clearly different in modality and domain.

### Decision
Build **LectureLens**: upload audio (or a YouTube URL) → Whisper transcribes → segments embedded with a sentence-transformer → FAISS semantic search → jump to timestamp. Phase 2 adds pyannote speaker diarization so search can be filtered by speaker ("find where a *student* asked about X").

### Consequences
- Different modality (audio) and architecture (ASR + retrieval) from the prior recommender — no "lazy/recycled" perception.
- The "semantic search over audio" capability is genuinely unknown to most users → satisfies the originality goal without overestimating scope.
- The speaker-filter feature gives a concrete, relatable demo ("jump to where a classmate asked the professor about X").
- No dataset dependency: users supply their own audio; evaluation uses public LibriSpeech. De-risks the "not enough data" failure mode.
- Trade-off: introduces a background-processing requirement (see ADR-006) because CPU transcription is slow.

---

## ADR-002: Whisper for transcription, run on CPU, with a file-size cap

**Date:** [today]
**Status:** Accepted

### Context
We need automatic speech recognition. Options: cloud APIs (OpenAI/Deepgram/AssemblyAI — paid, per-minute) vs. self-hosted Whisper (free, but CPU-bound on free tiers).

### Decision
Self-host **Whisper** (start with the `base` model; consider `faster-whisper` for speed). Run on CPU. Cap uploads at 50 MB (~30 min audio) for MVP to keep processing time and storage bounded.

### Consequences
- Free and self-contained; no per-minute API cost; strong "I built the ML pipeline" story.
- CPU transcription ≈ 5 min per hour of audio → mandates async processing (ADR-006).
- `faster-whisper` (CTranslate2 backend) can cut this materially and is a documented optimization for the portfolio.
- Larger Whisper models improve accuracy but increase memory/time; `base` is the MVP sweet spot on a 16 GB Space.
- Rejected cloud ASR: removes the core engineering story and adds cost; revisit only if CPU latency becomes a grading blocker.

---

## ADR-003: sentence-transformers (all-MiniLM-L6-v2) + FAISS for semantic search

**Date:** [today]
**Status:** Accepted

### Context
After transcription we need semantic (meaning-based) search over transcript segments, not keyword search.

### Decision
Embed each segment with **all-MiniLM-L6-v2** (80 MB, fast on CPU, 384-dim). Index in **FAISS** in-memory for MVP. Store segment metadata (recording_id, speaker_label, start_seconds) alongside for filtered search. Migrate to **Qdrant** in Phase 3 for persistence + native metadata filtering.

### Consequences
- MiniLM is small and fast — good for CPU and cheap to re-embed.
- FAISS in-memory is zero-ops but rebuilt on restart (cheap at our scale). Expose a `VectorStore` interface so the Qdrant swap is clean.
- Speaker-filtered search (Phase 2) needs metadata filtering: FAISS handles it via post-filtering for small N; Qdrant does it natively (a reason for the Phase 3 migration).
- Rejected pgvector: consolidating into Postgres is tempting but Neon free-tier pgvector is limited and we lose ANN tuning.

---

## ADR-004: Chunk transcripts into ~30s overlapping segments for embedding

**Date:** [today]
**Status:** Accepted

### Context
Whisper returns many short timestamped segments. Embedding each tiny segment gives noisy, contextless vectors; embedding the whole transcript loses timestamp granularity. We need a middle ground.

### Decision
Merge Whisper's raw segments into ~30-second windows (configurable) with a small overlap (~5 s) so context spanning a boundary isn't lost. Each window keeps its start/end timestamps. Search returns windows; the player jumps to `window.start_seconds`.

### Consequences
- Balances retrieval quality (enough context per vector) against jump precision (~30 s granularity is fine for "take me near that moment").
- Overlap prevents missing a concept that straddles a boundary.
- Chunking + timestamp mapping is pure logic → prime unit-test target (this is where a bug would send users to the wrong moment).
- Window size is a tunable we can evaluate in Phase 3 (Recall@K vs. window size).

---

## ADR-005: pyannote.audio for anonymous speaker diarization (Phase 2)

**Date:** [today]
**Status:** Accepted

### Context
Core differentiator: filter search by speaker. We need "who spoke when," but NOT "who is this real person" (privacy + scope).

### Decision
Use **pyannote.audio** to produce anonymous diarization (SPEAKER_00, SPEAKER_01, ...). Map diarization turns onto transcript segments by timestamp overlap. Users can rename labels ("Professor", "Student"). We never attempt identity recognition.

### Consequences
- Enables the headline demo ("jump to where a student asked about X").
- Anonymous-only diarization keeps us clear of biometric-identification ethics/privacy issues — stated explicitly to users (SPEC §9).
- pyannote on CPU is slow (2–3× real-time) → runs as a distinct, opt-in pipeline stage after transcription, with clear UI progress.
- pyannote gated models require a HuggingFace token + accepting model terms — document in `.env.example` and setup notes.
- Mapping diarization↔segments is pure logic → unit-testable with synthetic turns.

---

## ADR-006: ARQ + Redis for background processing

**Date:** [today]
**Status:** Accepted

### Context
Transcription (and especially diarization) take minutes. The HTTP API must not block. We need a task queue.

### Decision
Use **ARQ** (asyncio-native, lightweight) with **Redis** (Upstash free tier). Upload/YouTube endpoints enqueue a job and return immediately with `status=queued`. A worker runs the pipeline (download → transcribe → diarize → embed → index → summarize) and advances `recording.status` through stages. Frontend polls `/recordings/{id}/status`.

### Consequences
- Non-blocking API; resilient to long jobs; clear status model for the UI.
- ARQ chosen over Celery for simplicity (less config, asyncio-first) — adequate for a single worker at this scale.
- For MVP the worker can run in the same Space; can split into a dedicated worker later.
- Status state machine (queued→transcribing→diarizing→embedding→ready / failed) is unit-testable with mocked stages.
- Rejected synchronous processing (would time out and ruin UX) and rejected Celery (heavier than needed).

---

## ADR-007: YouTube ingestion via yt-dlp, marked as a bonus feature (Phase 2)

**Date:** [today]
**Status:** Accepted

### Context
Pasting a YouTube link and indexing the lecture massively increases usefulness, but yt-dlp depends on YouTube's changing internals.

### Decision
Support YouTube ingestion with **yt-dlp** (audio-only extraction → same pipeline). Pin a known-good version. Clearly mark it as a bonus; the core upload path must work independently so a yt-dlp breakage never takes down the demo.

### Consequences
- Big usefulness jump (index whole lecture series) for low marginal code.
- Isolated failure domain: if YouTube changes break yt-dlp during grading, only this feature degrades.
- Respect copyright/ToS: feature is for the user's own/permitted content; note in README.

---

## ADR-008: Python + FastAPI backend, Next.js + TypeScript frontend

**Date:** [today]
**Status:** Accepted

### Context
Owner has shipped Next.js/React/TS before and is learning Python+ML. Backend must host Python-native ML (Whisper, pyannote, embeddings).

### Decision
FastAPI (Python) backend; Next.js 14 App Router + TS strict + Tailwind frontend; JSON over HTTPS. The audio player + transcript sync is the main client-side complexity (HTML5 audio + a `useAudioPlayer` hook).

### Consequences
- Backend sits in the Python ML ecosystem (where the models live); frontend reuses existing strength and deploys fast on Vercel.
- Two services to deploy (backend+worker on HF Space, frontend on Vercel) — acceptable; each fits a free tier.
- Rejected all-JS (ONNX-in-browser Whisper exists but is immature and removes the Python-pipeline story).

---

## ADR-009: JWT (access + refresh) auth, bcrypt passwords

**Date:** [today]
**Status:** Accepted

### Context
Recordings are private and personal; peer reviewers rate security.

### Decision
bcrypt (cost 12) password hashing; JWT access token (15 min) + refresh token (7 d, httpOnly+Secure+SameSite=Strict cookie); slowapi rate limits on `/auth/login` and `/recordings/{id}/search`. Full threat model in `docs/SECURITY.md`.

### Consequences
- Reasonable XSS/CSRF balance (access token in memory, refresh in httpOnly cookie); documented explicitly.
- Per-user authorization enforced and tested on every recording route (audio is sensitive — IDOR here would be a real breach).

---

## ADR-010: pytest + Vitest, mock all ML in unit tests, coverage gates

**Date:** [today]
**Status:** Accepted

### Context
Unit tests are graded. ML models are too slow/heavy to load in unit tests.

### Decision
Backend: pytest + pytest-cov + httpx; inject `MockTranscriber`/`MockEmbedder`/`MockDiarizer` in unit tests. Integration tests use real Postgres + fake queue. Frontend: Vitest + RTL + MSW. CI gates: 70% overall, 90% on `services/` and `api/`. Worker pipeline tested via mocked stages asserting status transitions.

### Consequences
- Fast unit tests; the genuinely bug-prone logic (timestamp mapping, chunking, ranking, speaker filtering, auth) is well covered.
- 90% gate forces error-path tests, not just happy paths.

---

## ADR-011: Monorepo packaging — hatchling, optional-dependency extras, faster-whisper pin

**Date:** 2026-06-14
**Status:** Accepted

### Context
Scaffolding the repo required two packaging choices not fixed by CLAUDE.md. (1) CLAUDE.md lists every dependency across all three phases, including heavy/gated ML libs (pyannote.audio needs a HF token + accepted terms; yt-dlp is fragile to YouTube changes). Installing all of them for MVP work is slow and pulls in fragility before those phases exist. (2) CLAUDE.md says "openai-whisper (or faster-whisper)"; the README tech stack and ADR-002's optimization note both point at faster-whisper, but the PoC (`ml/scripts/poc_validation.py`) used openai-whisper.

### Decision
- **Build backend:** hatchling, flat `app/` layout (no `src/`), Python ≥3.11 — matches the CLAUDE.md tree.
- **Dependencies:** declare *all* CLAUDE.md deps, but isolate Phase 2 (`pyannote.audio`, `yt-dlp`, `keybert`) and Phase 3 (`onnxruntime`, `qdrant-client`) behind `[project.optional-dependencies]` extras `phase2` / `phase3`. MVP installs via `pip install -e ".[dev]"`; the full pipeline via `".[dev,phase2,phase3]"`.
- **Whisper:** pin `faster-whisper` as the Phase-1 ASR dependency.
- **CI:** installs MVP extras only (`.[dev]`) — Phase 2/3 heavy deps are excluded to keep CI fast and green; they get their own CI lane when those phases land.

### Consequences
- Light, fast MVP installs and CI; gated/fragile deps don't block day-one work or grading.
- The PoC keeps using openai-whisper (left untouched); production code targets faster-whisper. The transcription stage will be written against an interface so the backend isn't coupled to either implementation.
- Adds a small ritual: starting Phase 2/3 means installing the matching extra and extending CI.

---

## ADR Template

```
## ADR-XXX: [Title]
**Date:** YYYY-MM-DD
**Status:** Proposed | Accepted | Superseded by ADR-YYY
### Context
### Decision
### Consequences
```
