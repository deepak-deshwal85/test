# syntax=docker/dockerfile:1

ARG PYTHON_VERSION=3.13
FROM ghcr.io/astral-sh/uv:python${PYTHON_VERSION}-bookworm-slim

ENV PYTHONUNBUFFERED=1
ENV UV_COMPILE_BYTECODE=1
WORKDIR /app

# System deps once (cached unless base image changes)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ python3-dev curl \
  && rm -rf /var/lib/apt/lists/*

# Dependency layer cached unless lockfile changes
COPY pyproject.toml uv.lock ./
RUN mkdir -p src && uv sync --locked --no-install-project

# App code last — code-only changes skip uv sync
COPY . .
RUN uv sync --locked

ENV RAG_API_HOST=0.0.0.0
ENV RAG_API_PORT=8090
EXPOSE 8090
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8090"]
