#!/bin/sh
# First boot (with OPENROUTER_API_KEY or OPENAI_API_KEY): import eval/test_images through the
# same vision pipeline as POST /api/images, then start the API. Re-starts skip existing rows
# (eval:<filename> captions). Set SKIP_DB_SEED=1 to disable.

export PYTHONPATH=/app/app/backend

if [ "${SKIP_DB_SEED:-0}" = "1" ] || [ "${SKIP_DB_SEED:-0}" = "true" ]; then
  echo "docker-backend-entrypoint: SKIP_DB_SEED set — skipping library seed."
elif [ -n "${OPENROUTER_API_KEY:-}" ] || [ -n "${OPENAI_API_KEY:-}" ]; then
  echo "docker-backend-entrypoint: seeding library from eval/test_images (OpenRouter/OpenAI)..."
  python /app/eval/import_test_set_to_db.py --all-images \
    || echo "docker-backend-entrypoint: seed step failed — starting API anyway."
else
  echo "docker-backend-entrypoint: no LLM API key in env — skipping seed (add OPENROUTER_API_KEY to deploy/.env for a prepopulated library)."
fi

exec uvicorn fashion_backend.main:app --host "${API_HOST:-0.0.0.0}" --port "${API_PORT:-8000}"
