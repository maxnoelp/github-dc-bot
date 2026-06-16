FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Webhook-Port (an WEBHOOK_PORT anpassen, falls geändert).
EXPOSE 8080

CMD ["python", "bot.py"]
