# Use official Playwright image with browsers already installed
FROM mcr.microsoft.com/playwright/python:v1.47.0-focal

WORKDIR /opt/render/project/src

# Copy requirements & install deps (skip playwright, already in base image)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY . .

# Run the bot
CMD ["python", "bot.py"]
