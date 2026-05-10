# ============================================
# ITOps Platform Dockerfile
# ============================================
# Multi-stage build for optimized image size

# Stage 1: Builder
FROM python:3.11-slim as builder

WORKDIR /app

# Install build dependencies
# python:3.11-slim is based on Debian trixie (testing)
RUN echo 'deb https://mirrors.ustc.edu.cn/debian/ trixie main non-free-firmware' > /etc/apt/sources.list && \
    echo 'deb https://mirrors.ustc.edu.cn/debian-security/ trixie-security main non-free-firmware' >> /etc/apt/sources.list && \
    apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    libcurl4-openssl-dev \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --user --timeout=1200 -i https://pypi.tuna.tsinghua.edu.cn/simple/ -r requirements.txt

# Stage 2: Runtime
FROM python:3.11-slim

LABEL maintainer="ITOps Platform"
LABEL description="内网本地化AI辅助运维管理平台"

WORKDIR /app

# Install runtime dependencies
# python:3.11-slim is based on Debian trixie (testing)
RUN echo 'deb https://mirrors.ustc.edu.cn/debian/ trixie main non-free-firmware non-free' > /etc/apt/sources.list && \
    echo 'deb https://mirrors.ustc.edu.cn/debian-security/ trixie-security main non-free-firmware non-free' >> /etc/apt/sources.list && \
    apt-get update && apt-get install -y --no-install-recommends \
    chromium \
    chromium-sandbox \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set Playwright browser path
ENV PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH=/usr/bin/chromium-browser
ENV PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1

# Create non-root user
RUN groupadd -r itops && useradd -r -g itops itops

# Copy installed Python packages from builder
COPY --from=builder /root/.local /home/itops/.local

# Copy application code
COPY --chown=itops:itops . .

# Create necessary directories
RUN mkdir -p /app/logs /app/data /app/reports && \
    chown -R itops:itops /app

USER itops

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Default command
CMD ["python", "-m", "uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]