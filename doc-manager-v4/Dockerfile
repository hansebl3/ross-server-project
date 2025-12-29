FROM python:3.11-slim

WORKDIR /app

# Install system dependencies (needed for some python packages)
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Set PYTHONPATH to verify imports work
ENV PYTHONPATH=/app

# Default command (overridden by docker-compose)
CMD ["python", "src/watcher.py"]
