FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create .env placeholder (will be overridden by Cloud Run env vars)
RUN touch .env

# Expose port (Cloud Run uses PORT env var)
EXPOSE 8080

# Set default port
ENV PORT=8080

# Run the application using shell form to allow env var expansion
CMD uvicorn main:app --host 0.0.0.0 --port $PORT
