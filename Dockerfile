FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install dependencies before copying code so Docker can reuse this layer.
COPY requirements.txt .
RUN python -m pip install --no-cache-dir -r requirements.txt gunicorn==27.0.1

COPY . .

# Run without root privileges; only local database storage needs to be writable.
RUN useradd --create-home appuser \
    && mkdir -p /app/instance \
    && chown appuser:appuser /app/instance
USER appuser

EXPOSE 8000

CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "1", "--access-logfile", "-", "main:app"]
