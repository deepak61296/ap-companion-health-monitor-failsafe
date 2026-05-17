# Stage 1: Builder for building dependencies
FROM python:3.11-slim AS builder

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    python3-dev \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build

# Install requirements
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Stage 2: Final runtime image
FROM python:3.11-slim

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH

# Copy project files
COPY pyproject.toml .
COPY requirements.txt .
COPY src/ ./src/
COPY config/ ./config/

# Install the package in local mode
RUN pip install --no-cache-dir --no-deps .

# Environment
ENV MAVLINK20=1
ENV PYTHONUNBUFFERED=1

ENTRYPOINT ["python", "-m", "companion_health"]
CMD ["--help"]
