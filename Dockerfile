# Use Python 3.11 (greenlet compatible)
FROM python:3.11-slim

# Install system dependencies needed by Playwright
RUN apt-get update && apt-get install -y \
    wget gnupg ca-certificates curl unzip fonts-liberation \
    libasound2 libatk1.0-0 libatk-bridge2.0-0 libcups2 \
    libdbus-1-3 libdrm2 libxkbcommon0 libxcomposite1 \
    libxdamage1 libxfixes3 libxrandr2 libgbm1 libgtk-3-0 \
    libnss3 libxss1 libxtst6 libxshmfence1 xvfb \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright and Firefox browser
RUN pip install playwright && playwright install --with-deps firefox

# Copy project files
COPY . .

# Run bot
CMD ["python", "bot.py"]
