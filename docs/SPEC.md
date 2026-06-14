# LectureLens — Product Specification

> Search inside your recordings by meaning. Jump to the exact moment someone said what you're looking for.

**Version:** 0.1 (initial draft)
**Owner:** [your name]
**Course:** Full Stack Development, Master's in CS
**Status:** Active

---

## 1. Problem & Opportunity

Recorded lectures, meetings, and podcasts are functionally unsearchable. To find one explanation in a two-hour recording, you scrub through a timeline guessing. Existing transcription tools (Otter, Fireflies) offer only **keyword** search — typing "gradient descent" only matches those exact words, missing a segment that says "how the model reduces its error step by step."

Two ML capabilities, both largely unknown to non-technical users, solve this:
1. **Semantic search over audio** — find a moment by *meaning*, not exact words. (Most people don't know Whisper transcription or embedding search exist.)
2. **Speaker diarization** — automatically segment "who spoke when," so you can search within one speaker's turns ("find where a *student* asked about X" vs. "where the *professor* explained X").

LectureLens packages these into a tool a student can actually use: upload a lecture, then ask *"where did a classmate ask about overfitting?"* and jump straight to that timestamp.

## 2. Target Users

- **Primary:** Students reviewing recorded lectures who need to find specific explanations or Q&A moments fast.
- **Secondary:** Anyone with long recordings — podcast listeners, meeting attendees, researchers reviewing interview audio.
- **Tertiary (stretch):** People wanting to search across an entire library of recordings at once.

## 3. MVP Scope (Phase 1, Weeks 1–8)

User stories in priority order. MVP = stories 1–8.

1. As a user, I can sign up and log in with email + password.
2. As a user, I can upload an audio file (mp3/wav/m4a, up to 50 MB).
3. As a user, the system transcribes my upload in the background and notifies me when ready.
4. As a user, I can see a list of my recordings with status (processing / ready / failed).
5. As a user, I can open a recording and see its transcript with timestamps.
6. As a user, I can play the audio and click any transcript segment to jump to that moment.
7. As a user, I can search a recording with a natural-language query and get ranked, timestamped results.
8. As a user, I can click a search result to jump the audio player to that timestamp.

## 4. Phase 2 — Speaker-aware features (Weeks 9–14)

These are committed, not stretch. The speaker angle is core to the product story.

9. As a user, the system labels transcript segments by speaker ("Speaker 1", "Speaker 2", ...).
10. As a user, I can rename speakers ("Professor", "Student", "Me").
11. As a user, I can filter search to a specific speaker ("find where a *student* asked about X").
12. As a user, I can paste a YouTube URL and have its audio ingested and indexed like an upload.
13. As a user, I can see an auto-generated summary and topic tags for each recording.

## 5. Phase 3 — Engineering depth (Weeks 15–20)

14. As a user, I can search across all my recordings at once (cross-recording search).
15. Admin/metrics page reporting Word Error Rate (transcription) and Recall@K / MRR (search) on held-out sets.
16. The embedding model is exported to ONNX with INT8 quantization; latency before/after is documented.

## 6. Data Model

```
User
  id (uuid)
  email (unique)
  password_hash
  created_at

Recording
  id (uuid)
  user_id (FK)
  title
  source_type (enum: upload | youtube)
  source_url (nullable, for youtube)
  audio_path (object storage key)
  duration_seconds (nullable until processed)
  status (enum: queued | transcribing | diarizing | embedding | ready | failed)
  error_message (nullable)
  summary (text, nullable — Phase 2)
  created_at

Segment
  id (uuid)
  recording_id (FK)
  start_seconds (float)
  end_seconds (float)
  text
  speaker_label (string, nullable until diarized — Phase 2)
  embedding_id (reference into vector index)
  segment_index (int, ordering)

Speaker  (Phase 2 — user-friendly renames)
  recording_id (FK)
  raw_label (e.g. "SPEAKER_00")
  display_name (e.g. "Professor")
  PRIMARY KEY (recording_id, raw_label)

Topic  (Phase 2)
  recording_id (FK)
  label
  score
```

Vector index (FAISS MVP, Qdrant stretch): each Segment has a sentence-transformer embedding keyed by `segment.id`, with metadata `{recording_id, speaker_label, start_seconds}` for filtered search.

## 7. API Contract

All endpoints under `/api/v1`. JSON unless noted. JWT auth via `Authorization: Bearer <token>`.

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/auth/signup` | No | `{email, password}` → `{token, user}` |
| POST | `/auth/login` | No | `{email, password}` → `{token, user}` |
| POST | `/recordings` | Yes | Multipart audio upload OR `{youtube_url}`. Returns `{recording_id, status}`. Enqueues processing. |
| GET | `/recordings` | Yes | List user's recordings with status. |
| GET | `/recordings/{id}` | Yes | Recording detail + segments (transcript). |
| GET | `/recordings/{id}/status` | Yes | Poll processing status. |
| POST | `/recordings/{id}/search` | Yes | `{query, speaker?, limit}` → `{results: [{segment, score, start_seconds}], query_time_ms}` |
| PATCH | `/recordings/{id}/speakers` | Yes | `{raw_label, display_name}` rename (Phase 2). |
| POST | `/search` | Yes | Cross-recording search (Phase 3). |
| DELETE | `/recordings/{id}` | Yes | Delete recording + its segments + audio file. |
| GET | `/health` | No | Model load + DB + queue status. |

### Errors
Problem-details JSON: `{error: {code, message, details}}`. Codes: 400 validation, 401 auth, 403 forbidden, 404 not found, 413 payload too large, 429 rate limit, 500 server.

## 8. Processing Pipeline (the heart of the system)

```
Upload/YouTube → enqueue job → worker picks up:
  1. (youtube only) yt-dlp downloads audio
  2. Whisper transcribes → segments with timestamps
  3. (Phase 2) pyannote diarizes → speaker labels mapped onto segments
  4. sentence-transformer embeds each segment
  5. embeddings written to FAISS/Qdrant with metadata
  6. (Phase 2) KeyBERT topics + summary generated
  7. status → ready
```

Runs as a **background task queue** (ARQ or Celery + Redis), because Whisper on CPU is ~5 min/hour of audio and diarization is slower. The API never blocks on processing.

## 9. Non-Functional Requirements

### Performance
- Transcription throughput: roughly 5 min processing per 1 hour of audio (Whisper base, CPU). Communicated in UI.
- Search latency: p95 under 800 ms once a recording is indexed.
- Upload accepted and queued in under 2 s (processing happens async).

### Testing (graded course requirement)
- Backend: pytest, pytest-cov. 70% overall, 90% on `app/services` and `app/api`.
- ML logic unit-tested with mocks (never load Whisper/embedder in unit tests).
- Deterministic targets: chunking, timestamp↔segment mapping, ranking, speaker-filter logic, SM-2-style ordering, validation.
- Frontend: Vitest + React Testing Library (search bar, transcript view, audio player controls, recording list, auth).
- Evaluation scripts (Phase 3): WER on LibriSpeech, Recall@K/MRR on held-out queries.
- CI: GitHub Actions, lint + tests on every push.

### Deployment
- Backend (FastAPI + Whisper + embedder + FAISS) + worker: Hugging Face Space (free CPU: 2 vCPU, 16 GB, sleeps 48 h auto-wakes). Worker may run in the same Space process for MVP, separate later.
- Task queue: Redis on Upstash free tier.
- Frontend: Next.js on Vercel Hobby (free).
- Database: Postgres on Neon free tier.
- Object storage (audio files): Supabase Storage or Cloudflare R2 (10 GB free).
- Live URL available throughout peer-review window. Pre-index a sample recording so the demo is never empty.

### Security (peer-rated) — see SECURITY.md
- bcrypt passwords; JWT access + refresh; rate limits; Pydantic validation everywhere; per-user authorization (no IDOR); audio file validation by content; size caps; CORS allowlist; secrets in env.

### Accessibility
- WCAG 2.1 AA. Keyboard navigable. Transcript readable by screen readers. Captions/transcript ARE the accessibility win — lean into it.

### Privacy (important — audio is personal)
- Audio is processed, not mined. User can delete a recording and its audio + segments are removed.
- Diarization produces "Speaker 1/2", not identity recognition — we never try to identify *who* a person is, only separate distinct voices. Stated explicitly to users.
- If recording other people (e.g. a lecture), surface a one-time notice that users are responsible for consent where required.

## 10. Out of Scope

- Speaker *identification* (matching a voice to a real named person) — only anonymous diarization.
- Real-time / live transcription (batch upload only).
- Video processing (audio only; YouTube = audio track only).
- Languages: English MVP (Whisper supports more — multilingual is a stretch note, not a goal).
- Generating new audio / TTS.
- Payments, social features, mobile native apps.

## 11. Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Whisper too slow / times out on big files | High | High | 50 MB (~30 min) cap on MVP; async queue; show progress |
| Task queue adds backend complexity | High | Medium | Start with ARQ (simpler than Celery); single worker; document in ADR |
| pyannote diarization very slow on CPU (2–3× real-time) | High | Medium | Make diarization a separate, opt-in job stage; warn in UI |
| yt-dlp breaks due to YouTube changes | Medium | Medium | Mark YouTube ingest as bonus; upload path works independently; pin a known-good version |
| HF Space cold start with models loaded is slow | Medium | Medium | Warm-up ping before peer review; lazy-load models |
| Audio storage exceeds free tier | Medium | Low | Cap per-user storage; delete audio after N days option |
| Empty demo on first impression | Medium | High | Pre-index a CC-licensed sample talk so search works out of the box |
