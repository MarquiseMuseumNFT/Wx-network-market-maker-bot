# Use official slim Python base image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system deps (if needed for websockets/crypto/etc.)
RUN apt-get update && apt-get install -y \
    build-essential \ 
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the code
COPY . .

# Default command for Render worker (can be overridden in render.yaml)
CMD ["python", "bot.py"]
