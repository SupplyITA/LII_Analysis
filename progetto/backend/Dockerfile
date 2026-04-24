FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

RUN python -m playwright install --with-deps chromium

COPY src/ ./src/

EXPOSE 8003

CMD ["uvicorn", "src.server:app", "--host", "0.0.0.0", "--port", "8003"]
