FROM python:3.11-slim

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Create app directory
WORKDIR /locust

# Copy project files
COPY pyproject.toml .python-version ./
COPY locustfile.py load_test.py ./
COPY test_data/ /locust/test_data/

# Install dependencies using uv
RUN uv sync --frozen --no-dev

# Create directory for results
RUN mkdir -p /results

# Expose Locust ports
# 8089: Web UI
# 5557: Master communication
# 5558: Worker communication
EXPOSE 8089 5557 5558

# Set entrypoint to locust (via uv)
ENTRYPOINT ["uv", "run", "locust"]
