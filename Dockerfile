FROM python:3.11-slim

WORKDIR /app

RUN useradd -m -u 1001 appuser

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ ./app/
COPY scripts/ ./scripts/

RUN chown -R appuser:appuser /app
USER appuser

EXPOSE 5000 8000

HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
 CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:5000/health')"

CMD [ "python", "app/app.py" ]
 