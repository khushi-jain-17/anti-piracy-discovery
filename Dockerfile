FROM mcr.microsoft.com/playwright/python:v1.49.0-jammy

# Set working directory
WORKDIR /app

# Set environment variables for Python execution inside container
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Install additional Linux utilities if needed
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file first for Docker layer caching
COPY requirements.txt .

# Install Python packages and Chromium browser for Playwright
RUN pip install --no-cache-dir -r requirements.txt && \
    playwright install chromium

# Copy source code into container
COPY . .

# Ensure outputs directory structure exists inside container
RUN mkdir -p outputs/screenshots outputs/takedown_notices

# Volume mount point for output reports, evidence screenshots, and DMCA notices
VOLUME ["/app/outputs"]

# Default entrypoint for running the pipeline CLI
ENTRYPOINT ["python", "main.py"]
CMD ["--queries-per-lang", "5", "--max-results", "5"]
