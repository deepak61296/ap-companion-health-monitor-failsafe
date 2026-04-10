# Companion Computer Health Monitor Docker Image
#
# Build options:
#   1. With pre-built pymavlink wheel (fastest):
#      ./scripts/build_pymavlink_wheel.sh
#      docker build -t companion-health .
#
#   2. Build pymavlink from ArduPilot mavlink (includes COMPANION_HEALTH):
#      docker build --build-arg BUILD_PYMAVLINK=1 -t companion-health .
#
# Run:
#   docker run --rm -it --network host --privileged \
#     -v /sys:/sys:ro \
#     companion-health --device udpout:192.168.1.10:14550

ARG BUILD_PYMAVLINK=0

# =============================================================================
# Stage 1: Build pymavlink (only if BUILD_PYMAVLINK=1)
# =============================================================================
FROM python:3.10-slim AS pymavlink-builder

ARG BUILD_PYMAVLINK

RUN if [ "$BUILD_PYMAVLINK" = "1" ]; then \
        apt-get update && apt-get install -y git build-essential \
        && rm -rf /var/lib/apt/lists/*; \
    fi

WORKDIR /build

# Clone ArduPilot mavlink (has COMPANION_HEALTH)
RUN if [ "$BUILD_PYMAVLINK" = "1" ]; then \
        git clone --depth 1 --branch master \
        https://github.com/ArduPilot/mavlink.git; \
    fi

# Build pymavlink wheel
RUN if [ "$BUILD_PYMAVLINK" = "1" ]; then \
        pip install --no-cache-dir lxml cython && \
        cd /build/mavlink/pymavlink && \
        MDEF=/build/mavlink/message_definitions pip wheel . --no-deps -w /wheels; \
    else \
        mkdir -p /wheels; \
    fi

# =============================================================================
# Stage 2: Runtime image
# =============================================================================
FROM python:3.10-slim

WORKDIR /app

# Copy pre-built wheel if it exists in local wheels/ directory
COPY wheels/*.whl /tmp/wheels/ 2>/dev/null || true

# Copy wheel from builder stage (may be empty if BUILD_PYMAVLINK=0)
COPY --from=pymavlink-builder /wheels/*.whl /tmp/wheels/ 2>/dev/null || true

# Install pymavlink - prefer local wheel, then built wheel, then pip
RUN if ls /tmp/wheels/*.whl 1>/dev/null 2>&1; then \
        pip install --no-cache-dir /tmp/wheels/*.whl; \
    else \
        echo "Warning: No pymavlink wheel found, installing from pip"; \
        echo "This version may not include COMPANION_HEALTH message!"; \
        pip install --no-cache-dir pymavlink; \
    fi && \
    rm -rf /tmp/wheels

# Install other dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY companion_health/ ./companion_health/
COPY health_monitor.py .
COPY config.yaml.example .

# Verify COMPANION_HEALTH is available
RUN python -c "from pymavlink.dialects.v20 import ardupilotmega; \
    assert hasattr(ardupilotmega, 'MAVLINK_MSG_ID_COMPANION_HEALTH'), \
    'COMPANION_HEALTH message not found! Build with pre-built wheel or BUILD_PYMAVLINK=1'" \
    || echo "Warning: COMPANION_HEALTH verification failed"

# Environment
ENV MAVLINK20=1
ENV PYTHONUNBUFFERED=1

# Labels
LABEL org.opencontainers.image.title="Companion Health Monitor"
LABEL org.opencontainers.image.description="MAVLink health monitoring for ArduPilot companion computers"
LABEL org.opencontainers.image.source="https://github.com/ArduPilot/ardupilot"

ENTRYPOINT ["python", "health_monitor.py"]
CMD ["--help"]
