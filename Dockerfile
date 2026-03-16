# Stage 1: Build
FROM python:3.12-slim AS builder

RUN pip install --no-cache-dir uv

WORKDIR /app
COPY pyproject.toml .
COPY src/ src/

# Install dependencies and build
RUN uv pip install --system --no-cache . && \
    uv pip install --system --no-cache playwright

# Stage 2: Runtime
FROM python:3.12-slim

# Install system deps for Playwright
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        libnss3 libnspr4 libdbus-1-3 libatk1.0-0 libatk-bridge2.0-0 \
        libcups2 libdrm2 libxkbcommon0 libxcomposite1 libxdamage1 \
        libxfixes3 libxrandr2 libgbm1 libpango-1.0-0 libcairo2 \
        libasound2 libatspi2.0-0 && \
    rm -rf /var/lib/apt/lists/*

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin/argus /usr/local/bin/argus
COPY --from=builder /usr/local/bin/playwright /usr/local/bin/playwright

# Install Playwright browsers
ENV PLAYWRIGHT_BROWSERS_PATH=/opt/playwright
RUN playwright install chromium 2>/dev/null || true

# Create data directory
RUN mkdir -p /root/.argus

WORKDIR /app

ENTRYPOINT ["argus"]
CMD ["--help"]
