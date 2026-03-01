FROM python:3.13-slim AS builder
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
WORKDIR /app
COPY pyproject.toml uv.lock ./
COPY src/ src/
RUN uv sync --frozen --no-dev

FROM python:3.13-slim
WORKDIR /app
ARG BUILD_VERSION=dev
ENV APP_VERSION=${BUILD_VERSION}
COPY --from=builder /app/.venv .venv
COPY src/ src/
ENV PATH="/app/.venv/bin:$PATH"
CMD ["python", "-m", "telegram_notifier.main"]
