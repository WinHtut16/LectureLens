# LectureLens — backend

FastAPI API + ARQ worker + ML pipeline. See the root [`README.md`](../README.md)
for the full quick-start and [`CLAUDE.md`](../CLAUDE.md) for conventions.

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"                 # add ,phase2,phase3 for the full pipeline
cp .env.example .env
uvicorn app.main:app --reload           # API on :8000
arq app.worker.WorkerSettings           # background worker (separate terminal)
pytest                                   # tests + coverage
```
