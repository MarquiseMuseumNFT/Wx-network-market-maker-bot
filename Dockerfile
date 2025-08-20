# Use official Python image
FROM python:3.13-slim-bullseye

# Install system dependencies required by Playwright
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget \
    curl \
    ca-certificates \
    unzip \
    fonts-liberation \
    # GTK & graphics
    libgtk-4-1 \
    libgraphene-1.0-0 \
    libgles2-mesa \
    # GStreamer
    libgstreamer-gl1.0-0 \
    gstreamer1.0-plugins-base \
    gstreamer1.0-plugins-good \
    gstreamer1.0-plugins-bad \
    gstreamer1.0-libav \
    gstreamer1.0-plugins-ugly \
    libgstcodecparsers1.0-0 \
    # Misc runtime deps
    libenchant-2-2 \
    libsecret-1-0 \
    libmanette-0.2-0 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy project files
COPY . .

# Upgrade pip and install Python dependencies
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# Install only Chromium (lighter than all browsers)
RUN playwright install --with-deps chromium

# Set environment variables for headless Playwright
ENV PLAYWRIGHT_HEADLESS=1
ENV PYTHONUNBUFFERED=1

# Default command
CMD ["python", "bot.py"]
