FROM python:3.10-slim

# Imposta la directory di lavoro dentro il container
WORKDIR /app

# Copia il file dei requisiti e installa le librerie
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia tutto il resto del contenuto della cartella frontend/ (inclusi src/ e templates/)
COPY . .

# Espone la porta richiesta dalle specifiche
EXPOSE 8004

# Comando per avviare il server. Assicurati che punti a src.frontend:app
CMD ["uvicorn", "src.frontend:app", "--host", "0.0.0.0", "--port", "8004"]