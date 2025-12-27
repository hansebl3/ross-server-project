FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    git \
    procps \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY doc-manager/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy shared library
COPY shared /app/shared

# Copy all source code
COPY doc-manager .

# Expose port
EXPOSE 8505

# Run streamlit
# Run startup script (worker + streamlit)
CMD ["bash", "run_app.sh"]
