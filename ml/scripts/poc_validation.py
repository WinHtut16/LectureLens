"""
LectureLens POC Validation
--------------------------
1. Trim audio to 10 min
2. Transcribe with Whisper (base model)
3. Chunk segments into ~30 s windows
4. Embed each chunk with all-MiniLM-L6-v2
5. Run semantic queries and print ranked results
"""

import json
import os
import subprocess
import sys
import textwrap
import time
from pathlib import Path
from typing import List, Tuple

import numpy as np

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
AUDIO_INPUT = Path(r"d:\LectureLens\audios\test_audio_1.m4a")
AUDIO_CLIPPED = Path(r"d:\LectureLens\audios\test_clip_10min.wav")
CLIP_DURATION_SEC = 600  # 10 minutes
CHUNK_WINDOW_SEC = 30    # target chunk size
WHISPER_MODEL = "base"   # base is fast; switch to "small" for better accuracy

QUERIES = [
    "What is the main topic being discussed?",
    "Any questions asked by students or audience?",
    "Definitions or key concepts explained",
    "Examples or case studies mentioned",
    "Summary or conclusion of the lecture",
]

# ---------------------------------------------------------------------------
# Step 1 – Clip audio
# ---------------------------------------------------------------------------
def clip_audio(src: Path, dst: Path, duration: int) -> Path:
    if dst.exists():
        print(f"[clip] Using cached {dst.name}")
        return dst
    print(f"[clip] Trimming to {duration//60} min → {dst.name} ...")
    subprocess.run(
        [
            "ffmpeg", "-y",
            "-i", str(src),
            "-t", str(duration),
            "-ar", "16000",   # Whisper wants 16 kHz
            "-ac", "1",       # mono
            str(dst),
        ],
        check=True,
        capture_output=True,
    )
    print(f"[clip] Done → {dst}")
    return dst


# ---------------------------------------------------------------------------
# Step 2 – Transcribe with Whisper
# ---------------------------------------------------------------------------
def transcribe(audio_path: Path) -> List[dict]:
    import whisper  # type: ignore

    print(f"\n[transcribe] Loading Whisper '{WHISPER_MODEL}' model ...")
    t0 = time.time()
    model = whisper.load_model(WHISPER_MODEL)
    print(f"[transcribe] Model loaded in {time.time()-t0:.1f}s")

    print(f"[transcribe] Transcribing {audio_path.name} ...")
    t0 = time.time()
    result = model.transcribe(str(audio_path), verbose=False)
    elapsed = time.time() - t0
    segments = result["segments"]
    print(
        f"[transcribe] Done in {elapsed:.1f}s — "
        f"{len(segments)} segments, "
        f"{sum(len(s['text'].split()) for s in segments)} words"
    )
    return segments


# ---------------------------------------------------------------------------
# Step 3 – Chunk into ~30 s windows
# ---------------------------------------------------------------------------
def chunk_segments(segments: List[dict], window_sec: float = CHUNK_WINDOW_SEC) -> List[dict]:
    chunks = []
    current_text: List[str] = []
    chunk_start = 0.0
    chunk_end = 0.0

    for seg in segments:
        seg_start = seg["start"]
        seg_end = seg["end"]
        seg_text = seg["text"].strip()

        if not current_text:
            chunk_start = seg_start

        current_text.append(seg_text)
        chunk_end = seg_end

        if (chunk_end - chunk_start) >= window_sec:
            chunks.append(
                {
                    "start": chunk_start,
                    "end": chunk_end,
                    "text": " ".join(current_text),
                }
            )
            current_text = []
            chunk_start = seg_end

    # flush remaining
    if current_text:
        chunks.append(
            {
                "start": chunk_start,
                "end": chunk_end,
                "text": " ".join(current_text),
            }
        )

    print(f"\n[chunk] {len(chunks)} chunks of ~{window_sec}s from {len(segments)} segments")
    for i, c in enumerate(chunks):
        dur = c["end"] - c["start"]
        preview = c["text"][:80].replace("\n", " ")
        ts = f"{int(c['start'])//60}:{int(c['start'])%60:02d}"
        print(f"  [{i:2d}] {ts}  ({dur:.0f}s)  \"{preview}...\"")
    return chunks


# ---------------------------------------------------------------------------
# Step 4 – Embed chunks
# ---------------------------------------------------------------------------
def embed_chunks(chunks: List[dict]) -> np.ndarray:
    from sentence_transformers import SentenceTransformer  # type: ignore

    print(f"\n[embed] Loading all-MiniLM-L6-v2 ...")
    t0 = time.time()
    model = SentenceTransformer("all-MiniLM-L6-v2")
    print(f"[embed] Model loaded in {time.time()-t0:.1f}s")

    texts = [c["text"] for c in chunks]
    t0 = time.time()
    embeddings = model.encode(texts, show_progress_bar=True, normalize_embeddings=True)
    print(f"[embed] {len(texts)} chunks embedded in {time.time()-t0:.1f}s  shape={embeddings.shape}")
    return embeddings  # type: ignore[return-value]


# ---------------------------------------------------------------------------
# Step 5 – Semantic search (cosine via dot-product on unit vectors)
# ---------------------------------------------------------------------------
def search(
    query: str,
    chunks: List[dict],
    embeddings: np.ndarray,
    model,
    top_k: int = 3,
) -> List[Tuple[float, dict]]:
    q_vec = model.encode([query], normalize_embeddings=True)
    scores = (q_vec @ embeddings.T).flatten()
    top_idx = np.argsort(scores)[::-1][:top_k]
    return [(float(scores[i]), chunks[i]) for i in top_idx]


def run_queries(chunks: List[dict], embeddings: np.ndarray, queries: List[str]) -> None:
    from sentence_transformers import SentenceTransformer  # type: ignore

    print("\n[search] Loading embedding model for query encoding ...")
    model = SentenceTransformer("all-MiniLM-L6-v2")

    print("\n" + "=" * 72)
    print("SEMANTIC SEARCH RESULTS")
    print("=" * 72)

    for q in queries:
        results = search(q, chunks, embeddings, model, top_k=3)
        print(f"\nQuery: \"{q}\"")
        print("-" * 60)
        for rank, (score, chunk) in enumerate(results, 1):
            ts = f"{int(chunk['start'])//60}:{int(chunk['start'])%60:02d}"
            snippet = textwrap.fill(chunk["text"][:200], width=60, subsequent_indent="       ")
            print(f"  #{rank}  score={score:.3f}  @{ts}")
            print(f"       {snippet}")
        print()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> None:
    audio_clip = clip_audio(AUDIO_INPUT, AUDIO_CLIPPED, CLIP_DURATION_SEC)
    segments = transcribe(audio_clip)
    chunks = chunk_segments(segments)
    embeddings = embed_chunks(chunks)
    run_queries(chunks, embeddings, QUERIES)
    print("\n[done] POC complete. Evaluate results above.")


if __name__ == "__main__":
    main()
