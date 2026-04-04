#!/bin/sh
# Import eval/test_images on start (same pipeline as POST /api/images). With OPENROUTER_API_KEY
# or OPENAI_API_KEY: real vision calls. Without a key: mock classifier (still fills the library).
# Re-starts skip rows already present (eval:<filename> captions). SKIP_DB_SEED=1 disables.
#
# Keep the python invocation on ONE line — a trailing backslash before CRLF (Windows checkout)
# breaks line continuation in /bin/sh and the seed silently fails (then only "||" may run).

export PYTHONPATH=/app/app/backend

# Strip CR so deploy/.env with CRLF does not break comparisons (e.g. SKIP_DB_SEED=1\r).
SKIP_DB_SEED="$(printf '%s' "${SKIP_DB_SEED:-0}" | tr -d '\015')"

if [ "$SKIP_DB_SEED" = "1" ] || [ "$SKIP_DB_SEED" = "true" ]; then
  echo "docker-backend-entrypoint: SKIP_DB_SEED set — skipping library seed."
else
  if [ -n "${OPENROUTER_API_KEY:-}" ] || [ -n "${OPENAI_API_KEY:-}" ]; then
    echo "docker-backend-entrypoint: seeding library from eval/test_images (OpenRouter/OpenAI)..."
  else
    echo "docker-backend-entrypoint: no LLM API key — seeding with mock classifier (set OPENROUTER_API_KEY in deploy/.env for real vision)."
  fi
  echo "docker-backend-entrypoint: API will start after import finishes (one vision call per image; can take many minutes). nginx may 502 until then."
  if ! python /app/eval/import_test_set_to_db.py --all-images; then
    echo "docker-backend-entrypoint: seed step failed — see Python output above. Starting API anyway." >&2
  fi
fi

exec uvicorn fashion_backend.main:app --host "${API_HOST:-0.0.0.0}" --port "${API_PORT:-8000}"
