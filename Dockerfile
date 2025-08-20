# Dockerfile
FROM python:3.13-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright \
    PLAYWRIGHT_SKIP_VALIDATE_HOST_REQUIREMENTS=true

# System deps for Playwright/Chromium
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgtk-4-1 libgraphene-1.0-0 gstreamer1.0-gl gstreamer1.0-plugins-bad \
    libenchant-2-2 libsecret-1-0 libmanette-0.2-0 libgles2 \
    fonts-liberation ffmpeg \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Python deps (pin your Playwright here)
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# Install Playwright browsers INTO /ms-playwright (because of the ENV above)
RUN python -m playwright install --with-deps chromium

# App
COPY . .

CMD ["python", "test_wx.py"]
