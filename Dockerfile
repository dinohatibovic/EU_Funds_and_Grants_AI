# Base image
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Copy project files
COPY . /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
RUN pip install --upgrade pip
RUN pip install fastapi uvicorn sentence-transformers chromadb pdfplumber requests beautifulsoup4

# Expose API port
EXPOSE 8000

# Run FastAPI server
CMD ["uvicorn", "EU_Funds_and_Grants_AI.api.server:app", "--host", "0.0.0.0", "--port", "8000"]

