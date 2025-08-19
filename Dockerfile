# Base image
FROM python:3.13-slim

# Set working directory
WORKDIR /opt/render/project/src

# Install system dependencies for Playwright
RUN apt-get update && apt-get install -y \
    wget \
    curl \
    unzip \
    libnss3 \
    libx11-xcb1 \
    libxcomposite1 \
    libxcursor1 \
    libxdamage1 \
    libxi6 \
    libxtst6 \
    libglib2.0-0 \
    libgtk-3-0 \
    libdrm2 \
    libxrandr2 \
    libasound2 \
    libxss1 \
    libgbm1 \
    libxshmfence1 \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 🔥 Ensure Playwright + Firefox is installed in the container (build time)
RUN python -m playwright install --with-deps firefox

# Copy application code
COPY . .

# Run bot
CMD ["python", "bot.py"]
