FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:0.5.14 /uv /uvx /bin/
 
RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

ENV PATH="/app/.venv/bin:$PATH"
ENV UV_PROJECT_ENVIRONMENT=/app/.venv
ENV UV_LINK_MODE=copy
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app
ENV MODEL_PATH=/app/models/sentiment_analysis_model.pkl

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project

RUN python -m pytest --version && which python

COPY app/ ./app/
COPY models/ ./models/
COPY tests/ ./tests/


# Utente non privilegiato: il servizio deve solo leggere un file e rispondere.
RUN useradd --create-home appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]