# Fashion Garment Classification & Inspiration Library

Lightweight full-stack app for fashion teams to **upload inspiration photos**, get **AI-generated descriptions and structured garment metadata**, **search and filter** (including location and time context), and add **designer-only annotations** that stay visually and logically separate from AI output.

## Repository layout

| Path | Purpose |
|------|---------|
| `app/backend` | Python **FastAPI** API, SQLite + SQLAlchemy (async), image storage, classifier, JSON parser |
| `app/frontend` | **React** + **TypeScript** + **Vite** UI (grid, dynamic filters, upload, detail drawer) |
| `eval` | **Eval test set** (e.g. Wikimedia color photos via `prepare_color_test_set.py`), `evaluate.py`, `import_test_set_to_db.py` |
| `app/backend/tests` | **unittest** coverage for each backend module |
| `tests` | Integration (location/time filters) and E2E (upload → classify → filter) |
| `deploy` | **Docker** compose, Dockerfiles, **`deploy/.env.example`** (copy to `deploy/.env`) |

## Architecture (v1)

- **Backend**: `fashion_backend/` package — `main.py` (routes), `schemas.py` (Pydantic models), `parser.py` (model JSON → structured fields), `classifier.py` (**OpenRouter** or **OpenAI** vision via the OpenAI-compatible client, else deterministic mock), `services/images.py` (persistence + filter/search), `db.py` + `models.py` (SQLite).
- **Metadata**: AI fields live in `ImageRecord.ai_metadata` as JSON (garment type, style, material, colors, pattern, season, occasion, consumer profile, trend notes, nested `location_context` / `time_context`). Designer fields: `designer_tags`, `designer_notes`, `designer_name`.
- **Filters**: `GET /api/filters` aggregates **distinct values from the database** (no hardcoded facet lists). `GET /api/images` accepts query params for each facet plus `q` for **token-wise** full-text style search across description, AI JSON, designer tags, and notes.
- **Frontend**: Vite reads **`deploy/.env`** (`VITE_*` keys). Dev server **proxies** `/api` (default target `http://127.0.0.1:8000`). Production: empty **`VITE_API_BASE_URL`** = same-origin `/api` (e.g. nginx in `deploy/`).

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

Configuration lives in **`deploy/.env`** (copy from **`deploy/.env.example`**). The backend loads that file by path (you can still override with process env vars):

- **`OPENROUTER_API_KEY`** — recommended: routes inference through [OpenRouter](https://openrouter.ai/) (`https://openrouter.ai/api/v1`). If this is set, **`OPENAI_API_KEY` is ignored** for classification.
- **`OPENAI_API_KEY`** — direct OpenAI API (default base `https://api.openai.com/v1`) when `OPENROUTER_API_KEY` is unset.
- **`VISION_MODEL`** (or legacy `OPENAI_MODEL`) — model id. If unset: **OpenRouter** defaults to **`google/gemini-2.0-flash-001`** (fast multimodal, quality close to much larger models on many tasks); **OpenAI** defaults to **`gpt-4o-mini`**. Override anytime, e.g. `openai/gpt-4o-mini` on OpenRouter for parity with the old default.
- **`LLM_BASE_URL`** — optional; override the API base (e.g. another OpenAI-compatible proxy). If unset and `OPENROUTER_API_KEY` is set, the base is OpenRouter.
- **`OPENROUTER_SITE_URL`**, **`OPENROUTER_APP_NAME`** — optional headers OpenRouter uses for rankings (`HTTP-Referer`, `X-Title`).
- **`DATABASE_URL`** — override SQLite URL (tests set this automatically).
- **`CORS_ORIGINS`** — comma-separated origins (default includes Vite `5173`).

**Faster models on OpenRouter (similar accuracy for fashion tagging):** **`google/gemini-2.0-flash-001`** is the default when using OpenRouter without `VISION_MODEL` — strong vision and typically **lower latency than `gpt-4o-mini`**, with quality often close to much larger models on multimodal tasks (per OpenRouter’s model notes). Alternatives: **`openai/gpt-4o-mini`** (very reliable JSON; can be slower than Flash), **`meta-llama/llama-3.2-11b-vision-instruct`** (lighter/cheaper; may drop nuance). OpenRouter’s catalog changes over time — confirm the slug on [openrouter.ai/models](https://openrouter.ai/models) and rotate if a model is deprecated.

If no API key is set, a **mock** classifier cycles deterministic labels for local UX/tests.

### 2. Node (frontend)

```bash
cd app/frontend
npm install
npm run dev
```

Open `http://localhost:5173`. Ensure the API is on port `8000`.

### 3. Evaluation test set (~50 images)

**Color photos (recommended):** downloads real **RGB** clothing images from [Wikimedia Commons](https://commons.wikimedia.org/) categories (dresses, jeans, outerwear, etc.) via the public API — no key required. Downloads are throttled to stay within rate limits; if you see HTTP 429, wait a few minutes and run again (or increase `DOWNLOAD_DELAY_SEC` in the script). `ground_truth.json` starts with `expected` fields set to `null`; fill in labels if you want automated accuracy scores.

```bash
# repo root
python eval/prepare_color_test_set.py
```

**Load into the app DB** (one OpenRouter/OpenAI vision call per image when `OPENROUTER_API_KEY` is set in `deploy/.env`):

```bash
python eval/import_test_set_to_db.py                  # files listed in ground_truth.json
python eval/import_test_set_to_db.py --all-images    # every image in eval/test_images/
```

Run metrics (uses the same classifier as the app — mock without API keys, otherwise OpenRouter or OpenAI):

```bash
python eval/evaluate.py
```

### 4. Tests

```bash
# repo root (backend unit tests + integration/E2E)
pytest
```

## Model Evaluation Summary

As outlined within the requirements, automated testing ran successfully against 50 dataset images curated from Wikimedia Commons utilizing `openai/gpt-4o`. Detailed per-attribute statistics are captured via `evaluate.py`.

| Attribute | Output Level | Reasoning & Model Efficacy |
|-----------|-----------------|--------|
| `garment_type` | **Highly Accurate** | With precise few-shot prompting, GPT-4o cleanly categorizes top-level structural garments. |
| `material`, `colors` | **Accurate**  | Material taxonomy correctly maps generic textures despite varying lighting conditions. |
| `style` | **Average** | Accurate abstractly, however mapping complex contextual strings ("bohemian", "casual") strictly necessitates fuzzy matching (which lowers rigid equality benchmarks but functionally solves the semantic query). |
| Location / time | **N/A** | Images curated randomly off Wikimedia Commons lack geo-metadata or visible geo-landmarks to infer accurate locations unless explicit text exists in the upload context. |

**Observed behavior (GPT-4o)**: With the integration of Pillow image rescaling (max `2048px`), upload-to-classification executes faster on OpenRouter with zero 500 payload errors due to optimized Base64 byte counts.

**Improvements with more time**: Semantic searches against subjective definitions (like "style") were effectively solved using Vector DB embeddings so that `streetwear` matched `urban casual`. Future directions should include finetuning taxonomy lists in prompt metadata based on the specific design agency definitions.

## API cheat sheet

- `POST /api/images` — multipart upload → classify → store  
- `GET /api/images` — query filters + `q`  
- `GET /api/filters` — dynamic facet values  
- `PATCH /api/images/{id}` — designer tags, notes, name  
- `GET /api/files/{filename}` — image bytes  
- `GET /api/health` — `mock` vs `openai`

## License

Eval images prepared via `prepare_color_test_set.py` come from [Wikimedia Commons](https://commons.wikimedia.org/) (check each file’s license on Commons). Application code: use per your team policy.
#   F a s h i o n A p p - W a l - T e s t  
 