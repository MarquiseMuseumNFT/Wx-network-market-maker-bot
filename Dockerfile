FROM python:3.13-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# System deps for Chromium
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget gnupg libnss3 libx11-xcb1 libxcomposite1 libxcursor1 \
    libxdamage1 libxi6 libxtst6 libatk1.0-0 libatk-bridge2.0-0 \
    libcups2 libdrm2 libxrandr2 libgbm1 libasound2 \
    libpangocairo-1.0-0 libpango-1.0-0 libcairo2 \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# ⬇️ This bakes Chromium into the image
RUN playwright install --with-deps chromium

COPY . .

CMD ["python", "test_wx.py"]
