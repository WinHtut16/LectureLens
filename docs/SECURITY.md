# SECURITY.md

Threat model for LectureLens. Intentionally honest about what is and isn't defended. Peer reviewers should read this first.

**Last reviewed:** [date]

---

## Assets being protected

| Asset | Sensitivity |
|---|---|
| User accounts (email + password hash) | High — leak enables takeover + credential reuse |
| Uploaded audio recordings | **High** — may contain private lectures, meetings, voices of third parties |
| Transcripts & segments | High — verbatim content of the audio |
| Search queries | Low–medium — reveal user interests |
| Backend infra / free-tier quotas | Medium — abuse drains quotas, costs money |

Audio is the most sensitive asset here. A leaked recording is worse than a leaked favorites list — treat it accordingly.

## Threat actors considered

- **Curious peer reviewer** — probes auth, tries IDOR on `/recordings/{id}`, inspects network tab. (Most relevant for grading.)
- **Opportunistic internet attacker** — scanners, credential stuffing, brute force, malicious uploads.
- **Authenticated abuser** — tries to read others' recordings or exhaust transcription compute.

Not considered: nation-state, deep supply-chain attacks, physical security.

## Threats and mitigations

### Authentication & sessions
| Threat | Mitigation |
|---|---|
| Brute-force / credential stuffing on login | slowapi: 5 attempts / 15 min / IP. Generic "invalid credentials" error (no user enumeration). |
| Weak passwords | Min 10 chars, server-enforced via Pydantic validator. |
| Hash compromise | bcrypt cost 12. No MD5/SHA1, no reversible encryption. |
| Session theft via XSS | Access token in memory (not localStorage); refresh token in httpOnly + Secure + SameSite=Strict cookie; strict CSP. |
| CSRF | SameSite=Strict; state-changing routes require the Bearer header, not just the cookie. |
| Insecure transport | HTTPS only (platform certs); HSTS header. |
| Stale token after logout | Refresh-token deny list on logout. |
| JWT secret leak | Secret in env var, never committed; rotate if exposed. |

### Authorization (IDOR) — critical for audio privacy
| Threat | Mitigation |
|---|---|
| User A reads/deletes User B's recording by guessing the UUID | Every `/recordings/*` route checks `recording.user_id == current_user.id` before any read/modify/delete. Tested explicitly with a second account before this route ships. |
| Access to another user's audio file in object storage | Storage keys are unguessable UUIDs AND access is always brokered through the authorized API (no public bucket listing; signed URLs scoped to the owner). |
| Cross-user search leakage | Vector search is always filtered by `recording_id`s owned by the current user. Tested. |

### File upload (audio) — primary attack surface
| Threat | Mitigation |
|---|---|
| Malicious / disguised file (polyglot, fake extension) | Validate by content (`python-magic` magic bytes), not extension. Allowlist: mp3, wav, m4a, ogg only. |
| Oversized upload (DoS / quota drain) | 50 MB hard cap, enforced before full read (413 on exceed). |
| Decompression / duration bomb | Probe duration with ffmpeg before processing; reject > 30 min on MVP. |
| Malicious filename (stored XSS, path traversal) | Server assigns UUID storage keys; original filename never used in paths or echoed into HTML. |
| Transcription compute exhaustion | Per-user limits: max N concurrent jobs, max M uploads/hour. |

### YouTube ingestion (Phase 2)
| Threat | Mitigation |
|---|---|
| SSRF via crafted "youtube_url" pointing at internal services | Validate the URL is a real youtube.com/youtu.be host (allowlist), reject IPs/localhost/other schemes; yt-dlp restricted to the YouTube extractor. |
| Pulling enormous videos | Apply the same duration/size caps post-download; reject before processing. |

### Input validation
| Threat | Mitigation |
|---|---|
| SQL injection | SQLAlchemy ORM only; no string-interpolated SQL; Bandit lint in CI. |
| Oversized / malformed JSON | Pydantic v2 strict; body size limits. |
| Abusive search strings | Max query length 256 chars. |

### Rate limiting & resource abuse
| Threat | Mitigation |
|---|---|
| Search endpoint DoS | 60 req/min/user. |
| Job-queue flooding | Max concurrent + hourly upload caps per user. |
| Free-tier drain by bots | Optional Cloudflare in front if abuse observed. |

### Transport & infra
| Threat | Mitigation |
|---|---|
| MITM | HTTPS (HF Spaces/Vercel certs) + HSTS. |
| Misconfigured CORS | Explicit origin allowlist; no wildcard. |
| Mixed content | All assets over HTTPS; CSP enforces. |

### Dependencies
| Threat | Mitigation |
|---|---|
| Vulnerable / typosquatted package | Dependabot weekly; lockfiles pinned; PR review. yt-dlp pinned to a known-good version. |

### Privacy (audio-specific — take seriously)
| Concern | Stance |
|---|---|
| Recordings contain third parties' voices | Users are responsible for having the right to upload; a one-time notice states this. We process, we don't mine. |
| Voice biometrics | We do **anonymous** diarization only (Speaker 1/2). We never identify *who* a speaker is. Stated in-app. |
| Data retention | User can delete a recording → audio file + segments + embeddings removed. Optional auto-delete after N days. |
| Search/transcript exposure | Transcripts visible only to the owner; never public. |

## Known limitations / accepted risks
- Limited monitoring on free tier — a slow distributed brute force may go unnoticed.
- No 2FA on MVP (low-population demo; documented as future work).
- HF Space cold start (models loaded) can take up to ~60 s after 48 h idle — UX, not security.
- No formal disclosure program (course project).

## Pre-peer-review checklist
- [ ] Bandit + ruff: zero security warnings
- [ ] gitleaks: no secrets in history
- [ ] `.env.example` matches what the app reads
- [ ] CORS allowlist = deployed frontend origin
- [ ] HSTS on backend, CSP on frontend
- [ ] Rate limits active on `/auth/login` and `/recordings/{id}/search`
- [ ] Manual IDOR: second account cannot GET/DELETE another user's `/recordings/{id}` → 403/404
- [ ] Manual: signed storage URL from account A rejected for account B
- [ ] Manual: upload fake `.mp3` (actually a script) → rejected by magic-byte check
- [ ] Manual: 60 MB file → 413; 40-min audio → rejected
- [ ] Manual: malformed JSON / SQL-ish strings → 400/422 not 500
- [ ] Manual: expired token → 401; logout then reuse token → 401
- [ ] (Phase 2) Manual: `youtube_url` = `http://localhost:8000/health` → rejected (SSRF guard)
