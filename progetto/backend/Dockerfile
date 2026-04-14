FROM python:3.10-slim

WORKDIR /app

# Installa le librerie
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia il codice sorgente
COPY src/ ./src/

# Avvia il server sulla porta 8003
CMD ["uvicorn", "src.server:app", "--host", "0.0.0.0", "--port", "8003"]
