FROM python:3.11-slim
RUN apt-get update && apt-get install -y gcc libpq-dev && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ .
COPY web/ ./static_frontend/
RUN python manage.py collectstatic --noinput
EXPOSE 8000
CMD ["gunicorn","durai_backend.wsgi:application","--bind","0.0.0.0:8000","--workers","3","--timeout","120"]
