# Fashion Garment Classification & Inspiration Library

Lightweight full-stack app for fashion teams to **upload inspiration photos**, get **AI-generated descriptions and structured garment metadata**, **search and filter** (including location and time context), and add **designer-only annotations** that stay visually and logically separate from AI output.

## Repository layout

| Path | Purpose |
|------|---------|
| `app/backend` | Python **FastAPI** API, SQLite + SQLAlchemy (async), image storage, classifier, JSON parser |
| `app/frontend` | **React** + **TypeScript** + **Vite** UI (grid, dynamic filters, upload, detail drawer) |
| `eval` | Fashion-MNIST–derived **labeled test set** (50 images), `prepare_test_set.py`, `evaluate.py` |
| `tests` | Unit (parser), integration (location/time filters), E2E (upload → classify → filter) |

## Architecture (v1)

- **Backend**: `fashion_backend/` package — `main.py` (routes), `schemas.py` (Pydantic models), `parser.py` (model JSON → structured fields), `classifier.py` (OpenAI vision **or** deterministic mock), `services/images.py` (persistence + filter/search), `db.py` + `models.py` (SQLite).
- **Metadata**: AI fields live in `ImageRecord.ai_metadata` as JSON (garment type, style, material, colors, pattern, season, occasion, consumer profile, trend notes, nested `location_context` / `time_context`). Designer fields: `designer_tags`, `designer_notes`, `designer_name`.
- **Filters**: `GET /api/filters` aggregates **distinct values from the database** (no hardcoded facet lists). `GET /api/images` accepts query params for each facet plus `q` for **token-wise** full-text style search across description, AI JSON, designer tags, and notes.
- **Frontend**: Vite dev server **proxies** `/api` to `http://127.0.0.1:8000`. Production: serve `app/frontend/dist` behind any static host and point API with `VITE_API_URL` if needed (default empty = same origin).

## Setup

### 1. Python (backend + tests + eval)

```bash
cd Fashion-APP
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r app/backend/requirements.txt -r app/backend/requirements-dev.txt
```

Run API from `app/backend` (so `data/` and `uploads/` resolve correctly):

```bash
cd app/backend
python run.py
# or: uvicorn fashion_backend.main:app --reload --port 8000
```

Optional `.env` in `app/backend` (or env vars):

- `OPENAI_API_KEY` — if set, uploads use **OpenAI** vision (`OPENAI_MODEL`, default `gpt-4o-mini`). If unset, a **mock** classifier cycles deterministic labels for local UX/tests.
- `DATABASE_URL` — override SQLite URL (tests set this automatically).
- `CORS_ORIGINS` — comma-separated origins (default includes Vite `5173`).

### 2. Node (frontend)

```bash
cd app/frontend
npm install
npm run dev
```

Open `http://localhost:5173`. Ensure the API is on port `8000`.

### 3. Evaluation test set (50 images)

The eval set is the **first 50 samples** of the public [Fashion-MNIST](https://github.com/zalandoresearch/fashion-mnist) test split (open-source fashion/product images). Regenerate PNGs and `ground_truth.json` anytime:

```bash
# repo root, venv active
pip install pillow
python eval/prepare_test_set.py
```

Run metrics (uses the same classifier as the app — mock without `OPENAI_API_KEY`, OpenAI with key):

```bash
python eval/evaluate.py
```

### 4. Tests

```bash
# repo root
pytest tests -v
```

## Model evaluation summary (template)

| Attribute | Role in v1 eval | Notes |
|-----------|-----------------|--------|
| `garment_type` | **Labeled** in `ground_truth.json` (FMNIST class names) | Primary accuracy metric on the 50-image set |
| `style`, `material`, `occasion` | Omitted in ground truth (`null`) | Skipped in scoring until you add manual labels for photo datasets (e.g. Pexels) |
| Location / time | Omitted in ground truth | FMNIST has no real geography; extend JSON for street-style photos |

**Observed behavior (mock classifier)**: accuracy is **low** on FMNIST because the mock ignores pixels and hashes file bytes into one of three canned scenes. **With `OPENAI_API_KEY`**, expect higher `garment_type` agreement, with confusion on **similar silhouettes** (shirt vs t-shirt, coat vs jacket) due to low detail and grayscale.

**Improvements with more time**: fine-tuned vision classifier or structured-output fine-tuning; human-in-the-loop correction UI; active learning on failure cases; hybrid lexical + embedding search; FTS5 or pgvector for scale; per-team normalization rules for garment_type synonyms.

## API cheat sheet

- `POST /api/images` — multipart upload → classify → store  
- `GET /api/images` — query filters + `q`  
- `GET /api/filters` — dynamic facet values  
- `PATCH /api/images/{id}` — designer tags, notes, name  
- `GET /api/files/{filename}` — image bytes  
- `GET /api/health` — `mock` vs `openai`

## License

Dataset credit: Fashion-MNIST (Zalando Research, MIT). Application code: use per your team policy.
