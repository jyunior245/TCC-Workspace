FROM python:3.10-slim

WORKDIR /app

# Instala o netcat para o script de wait-for-db
RUN apt-get update && apt-get install -y netcat-openbsd && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

COPY wait-for-db.sh /wait-for-db.sh
RUN sed -i 's/\r$//' /wait-for-db.sh
RUN chmod +x /wait-for-db.sh

EXPOSE 5000

CMD ["/wait-for-db.sh", "python", "main.py"]
