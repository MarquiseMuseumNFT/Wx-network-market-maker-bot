FROM python:3.11-slim

# Install system dependencies required for browsers
RUN apt-get update && apt-get install -y \
    wget unzip curl gnupg ca-certificates \
    fonts-liberation libnss3 libatk1.0-0 libatk-bridge2.0-0 \
    libcups2 libdrm2 libxkbcommon0 libxcomposite1 libxrandr2 libxdamage1 \
    libxfixes3 libxshmfence1 libasound2 libatspi2.0-0 libwayland-client0 \
    libwayland-egl1 libwayland-cursor0 \
    && rm -rf /var/lib/apt/lists/*

# Set workdir
WORKDIR /app

# Copy deps and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright browsers (only Firefox)
RUN playwright install --with-deps firefox

# Copy source code
COPY . .

# Start bot
CMD ["python", "bot.py"]
