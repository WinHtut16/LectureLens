# LectureLens backend (API + ARQ worker) — skeleton image.
# Slim Python base with ffmpeg + libmagic for audio handling.
FROM python:3.11-slim

# System deps: ffmpeg (audio conversion), libmagic1 (content-based file validation).
RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg libmagic1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install MVP deps. Add phase2/phase3 extras when those stages deploy.
COPY pyproject.toml ./
RUN pip install --no-cache-dir -e ".[dev]"

COPY . .

EXPOSE 8000

# API. The worker runs the same image with: arq app.worker.WorkerSettings
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
