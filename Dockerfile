FROM python:3.11-slim

# Install system dependencies required for Chromium
RUN apt-get update && apt-get install -y curl unzip fonts-liberation \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY . .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Install Chromium only (lighter & avoids Firefox errors)
RUN npx playwright install --with-deps chromium

CMD ["python", "bot.py"]
