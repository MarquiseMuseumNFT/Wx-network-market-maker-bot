FROM python:3.11-slim

# Install system dependencies for Playwright
RUN apt-get update && apt-get install -y \
    wget \
    curl \
    libnss3 \
    libx11-xcb1 \
    libxcomposite1 \
    libxcursor1 \
    libxdamage1 \
    libxext6 \
    libxi6 \
    libxtst6 \
    libglib2.0-0 \
    libdrm2 \
    libgbm1 \
    libxrandr2 \
    libasound2 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libpangocairo-1.0-0 \
    libcups2 \
    libxss1 \
    libgtk-3-0 \
    && rm -rf /var/lib/apt/lists/*

# Set workdir
WORKDIR /app
COPY . .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright and Firefox browser
RUN pip install playwright && playwright install firefox

# Run bot
CMD ["python", "bot.py"]
