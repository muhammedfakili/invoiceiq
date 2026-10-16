# The API image: reading files, LLM extraction, validation and Excel export behind FastAPI.
# Built by docker-compose.yml (service "api"); the review screen has its own image (ui/Dockerfile).
FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:0.11.28 /uv /usr/local/bin/uv

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Packages first, code second: a code edit rebuilds in seconds.
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-default-groups --no-install-project

COPY app ./app
# Sample invoices for the "Try sample invoices" button (synthetic, see scripts/b1_dataset.py).
COPY data/invoices ./data/invoices

EXPOSE 8000
CMD ["uvicorn", "app.api:app", "--host", "0.0.0.0", "--port", "8000"]
