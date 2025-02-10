FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Verwijder de vaste poort 8000
EXPOSE $PORT

# Gebruik de $PORT environment variable
CMD gunicorn --bind 0.0.0.0:$PORT wsgi:app
