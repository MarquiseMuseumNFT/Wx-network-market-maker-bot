# Base image with Python & Playwright dependencies
FROM mcr.microsoft.com/playwright/python:v1.47.0-focal

# Set workdir
WORKDIR /opt/render/project/src

# Copy dependency list
COPY requirements.txt .

# Install Python deps
RUN pip install --no-cache-dir -r requirements.txt

# Install Firefox (headless) and system deps
RUN playwright install --with-deps firefox

# Copy bot code
COPY . .

# Run the bot
CMD ["python", "bot.py"]
