FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:0.12 /uv /bin/uv

WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy

COPY pyproject.toml uv.lock README.md ./
RUN --mount=type=cache,target=/root/.cache/uv uv sync --locked --no-dev --no-install-project

COPY src ./src
RUN --mount=type=cache,target=/root/.cache/uv uv sync --locked --no-dev

# Bake the default models into the image so the container starts without downloading them.
RUN uv run --no-sync python -c "from plate_reader_api.reader import PlateReader; PlateReader()"

EXPOSE 8000
CMD ["uv", "run", "--no-sync", "uvicorn", "plate_reader_api.main:app", "--host", "0.0.0.0", "--port", "8000"]
