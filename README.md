# Fashion Inspiration Library

Full-stack app to upload fashion inspiration images, run vision-based AI tagging, search and filter the library, and add designer annotations. This README focuses on **running everything locally with Docker** first, then documents **tests**, **model evaluation**, and how those map to a typical submission rubric.

## Table of contents

| Section | Links |
|---------|-------|
| **Overview** | [Architecture](#architecture) · [Tech stack](#tech-stack) ([Frontend](#frontend) · [Backend](#backend)) · [Supported functionality](#supported-functionality) · [Design choices and production outlook](#design-choices-and-production-outlook) ([limitations](#known-limitations) · [monitoring](#what-we-would-measure-and-test-in-production) · [first change](#first-change-if-shipping-for-real)) |
| **Run & develop** | [Run locally with Docker](#run-locally-with-docker) · [Local development without Docker](#local-development-without-docker) |
| **Repo & rubric** | [Repository layout](#repository-layout) · [Submission deliverables (rubric mapping)](#submission-deliverables-rubric-mapping) |
| **Quality** | [Model evaluation](#model-evaluation) · [Tests](#tests) |
| **Reference** | [API overview](#api-overview) · [License and data](#license-and-data) |

---

## Architecture

The app is a **classic three-tier setup** for local and container use: a **single-page web UI** talks to a **REST API**, which persists **metadata in SQLite** and **image bytes on disk** (or in a Docker volume). Upload and import paths send image bytes through a **vision LLM** (or a **mock** classifier when no API key is configured); the model returns JSON that is **parsed into structured garment and context fields** used for search, filters, and facets. **Evaluation scripts** under `eval/` call the same classification pipeline as the API so reported metrics match production behavior.

---

## Tech stack

### Frontend

| Layer | Technology |
|--------|------------|
| UI library | [React](https://react.dev/) 18 |
| Language | TypeScript |
| Build / dev server | [Vite](https://vitejs.dev/) |
| Production hosting | Static build served by [nginx](https://nginx.org/) (Alpine image in Docker); `/api` reverse-proxied to the backend |

### Backend

| Layer | Technology |
|--------|------------|
| API framework | [FastAPI](https://fastapi.tiangolo.com/) (ASGI) |
| Server | [Uvicorn](https://www.uvicorn.org/) |
| ORM / DB | [SQLAlchemy](https://www.sqlalchemy.org/) 2.x async with **SQLite** via `aiosqlite` |
| Storage | Local filesystem paths (`UPLOAD_DIR`, `DATA_DIR`); Docker Compose uses a named volume mounted at `/data` |
| Vision / LLM | OpenAI-compatible client ([OpenRouter](https://openrouter.ai/) or OpenAI) for multimodal chat + JSON; deterministic **mock** when no key is set |
| Config | Pydantic settings + `deploy/.env` |

### Deployment (local)

[Docker Compose](https://docs.docker.com/compose/) (`deploy/docker-compose.yml`) builds backend and frontend images from the **repository root**, runs both services on a default network, and persists SQLite and uploads in a **named volume**.

---

## Supported functionality

- **Image library** — Browse a grid of inspiration images with thumbnails served from the API.
- **Upload** — Upload new images; each file is **classified** (LLM or mock) and stored with **structured attributes** (e.g. garment type, style, material, color, pattern, season, occasion, location and time context).
- **Search & filters** — Query the library with text search (`q`) and filters such as garment type, style, material, occasion, location (continent / country / city), and time facets (year, month, season), plus designer-oriented fields where applicable.
- **Facets** — `GET /api/filters` exposes values present in the database for building filter UIs.
- **Designer workflow** — Update **designer tags, notes, and name** on records (`PATCH`).
- **Health / mode** — `GET /api/health` indicates service health and whether the **real LLM or mock** classifier is active.
- **Seeded demo data** — Docker backend entrypoint can **import** `eval/test_images/` through the same pipeline as upload (optional; configurable via env).
- **Evaluation** — Offline **per-attribute accuracy** against `eval/ground_truth.json` via `eval/evaluate.py` (see [Model evaluation](#model-evaluation)).
- **Automated tests** — Unit, integration, and E2E coverage (see [Tests](#tests)).

---

## Design choices and production outlook

### What we optimized for today

- **Vision tagging** — One **OpenAI-compatible** HTTP call per image (multimodal chat + JSON), with **image resizing** before the request to cap payload size and cost. The same path is used for uploads, seed imports, and offline evaluation so behavior stays comparable.
- **OpenRouter** — The project uses **OpenRouter** as the default provider because **no dedicated cloud credits** were available for first-party managed APIs (e.g. hyperscaler vision endpoints) or GPU hosting in this context. OpenRouter offers a single key and model selection via environment variables, which keeps local and Docker setups simple.
- **Persistence** — **SQLite** and **local filesystem** storage minimize operational overhead for development and coursework; **Chroma** (local) backs optional **text embeddings** for similarity search when an API key is configured.
- **Request path** — Uploads run **classification inline** in the `POST /api/images` handler (classify → write DB → then index for search). That trades **latency** on each upload for **straightforward correctness** and easier debugging.

### How this could look on cloud infrastructure

With budget for a cloud account, a typical production-shaped layout would separate concerns:

- **Blob storage** (e.g. S3, GCS, Azure Blob) for originals and derivatives (thumbnails, resized variants) instead of a single container volume.
- **Managed database** (e.g. **PostgreSQL**) for metadata, migrations, backups, and concurrent writers.
- **Secrets** in a vault or managed secret store, not only `.env` on disk.
- **Inference** behind a **dedicated API** or managed service—e.g. **Vertex AI**, **Azure OpenAI**, **Amazon Bedrock**, or a **self-hosted** vision model on **GPU** instances—chosen for SLAs, data residency, and cost controls rather than a generic multi-model router alone.

Exact vendor and topology are **not** prescribed here; they depend on compliance, latency targets, and pricing.

### How we would optimize inference for new data (e.g. uploads)

The current design is **synchronous**: the client waits for vision (and optional embedding) to finish. In a cloud-oriented system, the same product requirements would often push toward:

- **Async ingestion** — Accept the file, store it, enqueue a **job** (queue or workflow engine), return **202 + id** (or keep sync but stream progress). Workers run classification with **retries**, **backoff**, and **per-tenant rate limits**.
- **Deduping and caching** — **Content-hash** images so identical bytes skip repeat vision calls; cache structured outputs where safe.
- **Right-sized models** — Use a **smaller or specialized** vision / tagging model when quality is sufficient, reserving large VLMs for hard cases or human-in-the-loop review.
- **Batching and throttling** — Group non-latency-sensitive jobs to improve throughput and unit economics where the provider allows it.
- **Scale-out** — Run **stateless API** replicas separately from **GPU or high-latency inference workers** so spikes in uploads do not starve read traffic.

These are standard patterns; the README does not implement them end-to-end so the stack stays easy to run locally.

### Known limitations

Being explicit about gaps helps reviewers and interviewers ask the right follow-ups:

- **SQLite** — Strong fit for a single-node demo; weaker for many concurrent writers, online schema evolution, and HA than a managed **PostgreSQL** (or similar) tier.
- **No authn / authz** — The API assumes a trusted environment. A public deployment would need **identity**, **scopes**, upload **quotas**, and **abuse** controls.
- **Synchronous classification on upload** — The client waits for vision (and optional embedding). Slow models or large images mean **long requests** and **timeouts** unless the flow goes async (see above).
- **Third-party vision** — Quality, latency, and availability depend on **OpenRouter** and upstream model providers; **mock** mode is not a substitute for production semantics.
- **Local Chroma + embeddings** — The vector layer is **embedded** in the app process, not a managed, replicated search service; failures there are **best-effort** (lexical search still works).

### What we would measure and test in production

Not implemented here, but worth discussing in a systems or ML interview:

- **Latency** — p50 / p95 for `POST /api/images` (and time-to-visible in the grid if ingestion were async).
- **Reliability** — LLM **error rate**, **retry** behavior, and **degraded** behavior when the provider is down.
- **Cost** — **USD per classified image** (and per embedding), broken down by model; budgets and alerts.
- **Quality** — Periodic **offline eval** on a frozen slice (`eval/evaluate.py`-style) when prompts or models change; spot-checks for **schema drift** or nonsense attributes.
- **Synthetic checks** — **Health** endpoints, **smoke** uploads in staging, and **contract** tests on parsed JSON shape.

### First change if shipping for real

The **first** change would depend on context, but two common orderings are:

1. **If the API were exposed beyond a lab** — Add **authentication**, **rate limits**, and **auditability** before scaling inference.
2. **If traffic or latency dominated** — Move vision (and embeddings) to an **async worker** and return quickly after durable storage, as sketched in [How we would optimize inference for new data](#how-we-would-optimize-inference-for-new-data-eg-uploads).

Interviewers often want you to **justify the order** (risk vs throughput vs cost)—there is no single correct answer.

### For interviews

The paragraphs above are **intentionally concise**. **Tradeoffs** (cost vs quality, sync vs async UX, vendor lock-in, privacy and data retention, multi-region latency, evaluation drift when swapping models, auth vs async priority, etc.) are **left open** for discussion **during the interview**—this section is a starting point, not a closed design.

---

## Run locally with Docker

### Prerequisites

- [Docker](https://docs.docker.com/get-docker/) and [Docker Compose](https://docs.docker.com/compose/install/) (Compose V2: `docker compose`)

### 1. Configure environment

`deploy/.env.example` lists every variable you may need, including the LLM key names (`OPENROUTER_API_KEY`, `OPENAI_API_KEY`, and the rest). **Do not commit real API key values** to the repo or into the tracked example file; keep secrets only in gitignored `deploy/.env`. Any empty or sample values in `.env.example` are there for quick local copy-and-test, not as a pattern for sharing production keys.

From the repository root, copy the example file and then edit `deploy/.env` with your own values:

```bash
cp deploy/.env.example deploy/.env
```

In `deploy/.env`, set at least one of (optional for a quick demo):

- **`OPENROUTER_API_KEY`** — recommended ([OpenRouter keys](https://openrouter.ai/keys))
- **`OPENAI_API_KEY`** — optional alternative when OpenRouter is unset

Without a key, the API still runs; Docker **still seeds** the library from `eval/test_images/` using the **mock** classifier (see seeding below). Add a key for real vision tagging on import and uploads.

**Demonstration:** A working OpenRouter API key **is present** for demonstration purposes (kept only in gitignored `deploy/.env`, never committed). The app is wired end-to-end for live vision tagging with that setup. For a fresh environment without that file, copy `deploy/.env.example` to `deploy/.env` and set `OPENROUTER_API_KEY` (and any other values) yourself.

Other variables are documented inline in `deploy/.env.example` (CORS, models, upload limits, etc.).

### 2. Build and start

**From the repository root** (recommended):

```bash
docker compose -f deploy/docker-compose.yml --project-directory deploy up --build
```

**Or** from the `deploy` directory:

```bash
cd deploy
docker compose up --build
```

### 3. Open the app

| What | URL |
|------|-----|
| **Web UI** (nginx + static frontend) | [http://localhost:8080](http://localhost:8080) |
| **Backend API** (direct) | [http://localhost:8000](http://localhost:8000) |

The frontend proxies API calls to the backend at **`/api`** (same origin on port 8080). The backend is also exposed on port **8000** for direct use or debugging.

### First start: database seeding

On each backend start (unless disabled), the container runs `import_test_set_to_db.py --all-images`: it imports everything under `eval/test_images/` using the same pipeline as `POST /api/images`. **With** an API key that uses real vision; **without** a key it uses the **mock** classifier so you still get a populated grid. **Restarts** skip rows that are already in the database (`eval:<filename>` captions).

- To **disable** seeding entirely: set `SKIP_DB_SEED=1` in `deploy/.env` (or under `backend.environment` in `docker-compose.yml`).

### Data persistence

SQLite, uploads, and app data live in the Docker volume **`fashion_data`** (mounted at `/data` in the backend container). Removing the volume clears the library:

```bash
docker compose -f deploy/docker-compose.yml --project-directory deploy down -v
```

### Stop

```bash
docker compose -f deploy/docker-compose.yml --project-directory deploy down
```

---

## Repository layout

Layout matches a common **submission spec**: application under `app/`, evaluation assets under `eval/`, top-level API tests under `tests/`, plus co-located backend unit tests.

| Path | Purpose |
|------|---------|
| `app/backend` | FastAPI API, SQLite, image storage, LLM classification, parser, `fashion_backend` package |
| `app/frontend` | React + TypeScript + Vite UI |
| `app/backend/tests` | Backend unit tests (e.g. model output parsing, classifier config) |
| `eval` | Labeled test set (`ground_truth.json`), `test_images/`, `evaluate.py`, import helpers, `evaluation_report.md` |
| `tests` | Integration tests (filters) and end-to-end tests (HTTP API) |
| `deploy` | `docker-compose.yml`, Dockerfiles, `nginx` config, `.env.example` |

---

## Submission deliverables (rubric mapping)

| Expectation | Where it lives in this repo |
|-------------|----------------------------|
| **Web app**, minimal local setup, README with setup + architecture | Docker and dev instructions above; **Architecture** section; API summary below |
| **Model evaluation** — 50–100 fashion/garment images, manual expected attributes, classifier run, **per-attribute accuracy** (garment type, style, material, occasion, **location**), short analysis | `eval/test_images/` (populate with `eval/prepare_color_test_set.py` or your own images), labels in `eval/ground_truth.json` (~50 entries in-repo), run `eval/evaluate.py` → console + `eval/evaluation_report.md`. Location is scored as `continent` / `country` / `city`. **Time** context is modeled in metadata and filters but not in the accuracy table unless you extend `evaluate.py`. |
| **Unit test** — parsing model output into structured attributes | `app/backend/tests/parser_tests.py` (`parse_model_output`, `normalize_raw_payload`) |
| **Integration test** — filter behavior, **especially location and time** | `tests/test_filters_integration.py` (`country`+`year`, `continent`+`month`, `time_season` + `city` via service layer) |
| **End-to-end test** — upload, classify, filter | `tests/test_e2e_upload_classify_filter.py` (`POST /api/images`, then `GET /api/images` by `garment_type`, then `GET /api/filters`) |
| **`/app`**, **`/eval`**, **`/tests`**, **README** | `app/`, `eval/`, `tests/`, this file |

For review, prefer **logical git commits** (e.g. backend, frontend, eval set, tests, docs) so the story of the work is easy to follow.

---

## Model evaluation

**Test set:** The repo is set up for **at least 50** labeled rows in `eval/ground_truth.json`, with files under `eval/test_images/` (e.g. Wikimedia Commons–sourced fashion photos; you can also use other open datasets or sources such as [Pexels fashion search](https://www.pexels.com/search/fashion/) if licenses allow). If `test_images` is empty, run from the **repository root**:

```bash
pip install -r app/backend/requirements.txt
python eval/prepare_color_test_set.py
```

That script downloads on the order of **50** images and writes/merges `ground_truth.json` (expected fields may be null until you fill them manually for strict accuracy). Optional: `eval/prepare_hf_fashion_sample.py` + `eval/requirements-hf.txt` for additional sampling.

**Run the evaluator** (uses `OPENROUTER_API_KEY` or `OPENAI_API_KEY` from the environment, or **mock** if unset — mock scores are not semantically meaningful):

```bash
# Load secrets the same way as local dev, e.g. from deploy/.env (do not commit keys)
python eval/evaluate.py
```

This classifies each image with the same pipeline as the API, compares to `expected` in `ground_truth.json`, prints **per-attribute accuracy** for `garment_type`, `style`, `material`, `occasion`, and location fields, and overwrites `eval/evaluation_report.md` with the numeric summary plus a short template **Analysis** section. For a real submission, edit that analysis (or this README) with honest notes on **where the model does well**, **where it struggles**, and **what you would improve** (prompting, taxonomy, fine-tuning, more labeled data, etc.).

---

## Local development without Docker

Use the same `deploy/.env` file.

**Backend** — from the **repository root**, create a venv, install dependencies, then run the app from `app/backend`:

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
pip install -r app/backend/requirements.txt -r app/backend/requirements-dev.txt
cd app/backend
python run.py
```

**Frontend**:

```bash
cd app/frontend
npm install
npm run dev
```

Open [http://localhost:5173](http://localhost:5173); the dev server proxies `/api` to the backend (see `VITE_DEV_PROXY_TARGET` in `.env.example`).

---

## Tests

**Install** (from repository root):

```bash
pip install -r app/backend/requirements.txt -r app/backend/requirements-dev.txt
```

**Full suite** — `pytest.ini` collects `tests/` and `app/backend/tests/` and enforces high coverage on `fashion_backend`:

```bash
pytest
```

**Rubric-focused subset** (faster feedback; bypasses the global coverage threshold from `addopts`):

```bash
pytest app/backend/tests/parser_tests.py tests/test_filters_integration.py tests/test_e2e_upload_classify_filter.py --no-cov
```

| Rubric item | Test file | What it asserts |
|-------------|-----------|-----------------|
| Parse LLM JSON into structured attributes | `app/backend/tests/parser_tests.py` | Fenced JSON, nested/flat shapes, `location_context` / `time_context` coercion, list fields |
| Location + time **filters** on stored metadata | `tests/test_filters_integration.py` | HTTP `GET /api/images` with `country`, `year`, `continent`, `month`; service-layer `time_season` + `city` |
| Upload → classify → filter (E2E) | `tests/test_e2e_upload_classify_filter.py` | `POST /api/images` returns `structured.garment_type`; listing by that type includes the new row; `GET /api/filters` returns facets |

Other backend modules (DB, schemas, classifier, embeddings, etc.) have additional tests under `app/backend/tests/`.

---

## API overview

- `POST /api/images` — upload → classify → store  
- `GET /api/images` — filters and search (`q`)  
- `GET /api/filters` — facet values from the database  
- `PATCH /api/images/{id}` — designer fields  
- `GET /api/files/{filename}` — image bytes  
- `GET /api/health` — health / classifier mode  

---

## License and data

Eval images under `eval/` may come from [Wikimedia Commons](https://commons.wikimedia.org/); check each file’s license on Commons. Application code: per your team policy.
