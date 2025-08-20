# Dockerfile
FROM python:3.13-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# ---- System deps needed by Playwright headless browsers ----
ARG DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgtk-4-1 \
    libgraphene-1.0-0 \
    gstreamer1.0-gl \
    gstreamer1.0-plugins-bad \
    libenchant-2-2 \
    libsecret-1-0 \
    libmanette-0.2-0 \
    libgles2 \
    fonts-liberation \
    ffmpeg \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python deps first (better layer caching)
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# Install Playwright browsers during build (not on every start)
# You can restrict to only the engines you need.
RUN python -m playwright install chromium firefox webkit

# Copy the rest of the app
COPY . .

# Start the bot
CMD ["python", "bot.py"]
