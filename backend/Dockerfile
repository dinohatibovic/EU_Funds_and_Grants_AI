# FinAssistBH Backend — build context je ROOT repozitorija:
#   docker build -f backend/Dockerfile .
# (docker-compose u infrastructure/ to već radi ispravno)
FROM python:3.12-slim

WORKDIR /app

# Sistemske zavisnosti
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Prvo requirements (Docker layer cache — brži rebuild)
COPY ai_core/requirements.txt ai_core/requirements.txt
COPY backend/requirements.txt backend/requirements.txt
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r ai_core/requirements.txt -r backend/requirements.txt

# Kod i podaci
COPY ai_core/ ai_core/
COPY backend/ backend/
COPY data/ data/

EXPOSE 8000

CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
