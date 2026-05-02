# --- base: shared system deps + production Python packages ---
FROM python:3.11-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        postgresql-client \
        build-essential \
        libpq-dev \
        libmagic1 \
        curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# --- dev: base + development/test packages (used by docker-compose) ---
FROM base AS dev

COPY requirements-dev.txt /app/
RUN pip install --no-cache-dir -r requirements-dev.txt

COPY . /app/

EXPOSE 8000
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]

# --- production: base + hardened for deployment ---
FROM base AS production

COPY . /app/

RUN mkdir -p /app/logs \
    && python manage.py collectstatic --noinput || true \
    && addgroup --system django \
    && adduser --system --ingroup django django \
    && chown -R django:django /app

USER django

EXPOSE 8000
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "3", "core.wsgi:application"]
