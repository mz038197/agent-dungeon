FROM python:3.12-slim-bookworm

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends git ca-certificates libportaudio2 \
    && rm -rf /var/lib/apt/lists/*

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    STUDIO_CLOUD_MODE=1 \
    PEAS_AGENT_HOME=/data/peas-agent

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project

COPY . .
RUN sed -i 's/\r$//' scripts/entrypoint.sh \
    && chmod +x scripts/entrypoint.sh \
    && uv sync --frozen

EXPOSE 8501

ENTRYPOINT ["scripts/entrypoint.sh"]
