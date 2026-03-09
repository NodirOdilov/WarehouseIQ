version: "3.9"

services:
  db:
    image: postgres:16-alpine
    container_name: warehouseiq_db
    restart: unless-stopped
    environment:
      POSTGRES_DB: ${POSTGRES_DB:-warehouseiq}
      POSTGRES_USER: ${POSTGRES_USER:-warehouseiq}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-warehouseiq_secret}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "${POSTGRES_PORT:-5432}:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER:-warehouseiq}"]
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    container_name: warehouseiq_redis
    restart: unless-stopped
    command: redis-server --requirepass ${REDIS_PASSWORD:-redis_secret}
    ports:
      - "${REDIS_PORT:-6379}:6379"
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "-a", "${REDIS_PASSWORD:-redis_secret}", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    container_name: warehouseiq_backend
    restart: unless-stopped
    command: >
      sh -c "python manage.py migrate --noinput &&
             daphne -b 0.0.0.0 -p 8000 config.asgi:application"
    environment:
      - DJANGO_SETTINGS_MODULE=config.settings.production
      - DATABASE_URL=postgres://${POSTGRES_USER:-warehouseiq}:${POSTGRES_PASSWORD:-warehouseiq_secret}@db:5432/${POSTGRES_DB:-warehouseiq}
      - REDIS_URL=redis://:${REDIS_PASSWORD:-redis_secret}@redis:6379/0
      - CELERY_BROKER_URL=redis://:${REDIS_PASSWORD:-redis_secret}@redis:6379/1
      - SECRET_KEY=${SECRET_KEY:-change-me-in-production}
      - DEBUG=${DEBUG:-False}
      - ALLOWED_HOSTS=${ALLOWED_HOSTS:-*}
      - CORS_ALLOWED_ORIGINS=${CORS_ALLOWED_ORIGINS:-http://localhost,http://localhost:3000}
    volumes:
      - ./backend:/app
      - static_files:/app/staticfiles
      - media_files:/app/media
    ports:
      - "8000:8000"
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_healthy

  celery_worker:
    build:
      context: ./backend
      dockerfile: Dockerfile
    container_name: warehouseiq_celery_worker
    restart: unless-stopped
    command: celery -A config worker -l info --concurrency=4
    environment:
      - DJANGO_SETTINGS_MODULE=config.settings.production
      - DATABASE_URL=postgres://${POSTGRES_USER:-warehouseiq}:${POSTGRES_PASSWORD:-warehouseiq_secret}@db:5432/${POSTGRES_DB:-warehouseiq}
      - REDIS_URL=redis://:${REDIS_PASSWORD:-redis_secret}@redis:6379/0
      - CELERY_BROKER_URL=redis://:${REDIS_PASSWORD:-redis_secret}@redis:6379/1
      - SECRET_KEY=${SECRET_KEY:-change-me-in-production}
    volumes:
      - ./backend:/app
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_healthy

  celery_beat:
    build:
      context: ./backend
      dockerfile: Dockerfile
    container_name: warehouseiq_celery_beat
    restart: unless-stopped
    command: celery -A config beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler
    environment:
      - DJANGO_SETTINGS_MODULE=config.settings.production
      - DATABASE_URL=postgres://${POSTGRES_USER:-warehouseiq}:${POSTGRES_PASSWORD:-warehouseiq_secret}@db:5432/${POSTGRES_DB:-warehouseiq}
      - REDIS_URL=redis://:${REDIS_PASSWORD:-redis_secret}@redis:6379/0
      - CELERY_BROKER_URL=redis://:${REDIS_PASSWORD:-redis_secret}@redis:6379/1
      - SECRET_KEY=${SECRET_KEY:-change-me-in-production}
    volumes:
      - ./backend:/app
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_healthy

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    container_name: warehouseiq_frontend
    restart: unless-stopped
    volumes:
      - frontend_build:/app/build
    depends_on:
      - backend

  nginx:
    image: nginx:1.25-alpine
    container_name: warehouseiq_nginx
    restart: unless-stopped
    ports:
      - "${NGINX_PORT:-80}:80"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/conf.d/default.conf:ro
      - static_files:/var/www/static:ro
      - media_files:/var/www/media:ro
      - frontend_build:/var/www/frontend:ro
    depends_on:
      - backend
      - frontend

volumes:
  postgres_data:
  redis_data:
  static_files:
  media_files:
  frontend_build:
