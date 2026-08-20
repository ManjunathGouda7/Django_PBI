# Use lightweight Python 3.12 slim base image
FROM python:3.12-slim

# Prevent Python from writing .pyc files & enable unbuffered logging
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt gunicorn

# Copy project source code
COPY . /app/

# Create non-root app user
RUN useradd -m -u 1000 appuser && \
    mkdir -p /app/BI/media /app/BI/static && \
    chown -R appuser:appuser /app

USER appuser

# Expose port 8000
EXPOSE 8000

# Set working directory to Django app directory
WORKDIR /app/BI

# Healthcheck
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD curl -f http://localhost:8000/login/ || exit 1

# Command to run Gunicorn production WSGI server
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "3", "BI.wsgi:application"]

