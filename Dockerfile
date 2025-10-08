# Minimal Dockerfile for PersonaOCEAN
# Base: slim Python for smaller image
FROM python:3.13-slim

# Ensure stdout/stderr are unbuffered
ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# Set workdir
WORKDIR /app

# System deps (if needed for building wheels). Keep minimal.
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
 && rm -rf /var/lib/apt/lists/*

# Copy only requirements first for better layer caching
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Default environment (override in runtime)
ENV LOG_LEVEL=INFO

# Run the bot (uses DISCORD_BOT_TOKEN from env)
CMD ["python", "-u", "main.py"]
