FROM python:3.11-slim-bookworm

# Install DuckDB dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:0.5.10 /uv /uvx /bin/

# Copy the project into the image
WORKDIR /app
COPY pyproject.toml ./
COPY uv.lock ./

# Install dependencies using uv
RUN uv sync --frozen --no-cache

COPY . .

# Set up environment variables
ENV PATH="/app/.venv/bin:$PATH"
ENV DUCKDB_PATH="/data/db.duckdb"
ENV MODEL_REGISTRY_PATH="/data/models"

# Expose port
EXPOSE 8000

# Start API
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
