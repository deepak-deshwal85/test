# syntax=docker/dockerfile:1

ARG PYTHON_VERSION=3.13
FROM ghcr.io/astral-sh/uv:python${PYTHON_VERSION}-bookworm-slim

ENV PYTHONUNBUFFERED=1
WORKDIR /app

RUN apt-get update && apt-get install -y gcc g++ python3-dev \
  && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml uv.lock ./
RUN mkdir -p src
RUN uv sync --locked

COPY . .

EXPOSE 8090
CMD ["uv", "run", "python", "scripts/run_rag_api.py", "--host", "0.0.0.0", "--port", "8090"]
