FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Je kunt desgewenst een vaste poort EXPOSEn, maar $PORT wordt pas runtime gevuld.
# Voor local debugging kun je gewoon EXPOSE 8000 doen, bijvoorbeeld:
EXPOSE 8000

# Gebruik de JSON-array met een mini-shellcommando.
# De shell (sh -c) zorgt ervoor dat $PORT wél wordt uitgebreid,
# en `exec` laat gunicorn netjes PID 1 worden voor signaalafhandeling.
CMD ["sh", "-c", "exec gunicorn --bind 0.0.0.0:${PORT:-8000} wsgi:app"]
