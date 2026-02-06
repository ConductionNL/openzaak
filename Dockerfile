# OpenZaak ExApp for Nextcloud
# Wraps OpenZaak ZGW APIs with AppAPI integration
#
# OpenZaak is the reference implementation of the ZGW (Zaakgericht Werken) APIs.
# It requires:
# - PostgreSQL with PostGIS extension
# - Redis for caching
#
# See: https://open-zaak.readthedocs.io/

# Use upstream OpenZaak image as base (already has Django, uwsgi, PostGIS libs, etc.)
FROM openzaak/open-zaak:1.13.0

# Install additional dependencies for ExApp wrapper
USER root

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    tini \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies for ExApp wrapper (FastAPI, uvicorn, httpx)
RUN pip install --no-cache-dir \
    "fastapi>=0.109.0" \
    "uvicorn>=0.27.0" \
    "httpx>=0.26.0"

# Copy ExApp wrapper
COPY ex_app /app/ex_app
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Create directories for media and static files
RUN mkdir -p /app/media /app/static /app/log && \
    chown -R nobody:nogroup /app/media /app/static /app/log 2>/dev/null || true

WORKDIR /app

# Environment variables (set by AppAPI)
ENV APP_HOST=0.0.0.0
ENV APP_PORT=9000
ENV PYTHONUNBUFFERED=1

# OpenZaak configuration
ENV OPENZAAK_PORT=8000
ENV DJANGO_SETTINGS_MODULE=openzaak.conf.docker

# OpenZaak requires these to be set (defaults for development)
ENV DB_HOST=localhost
ENV DB_NAME=openzaak
ENV DB_USER=openzaak
ENV DB_PASSWORD=openzaak
ENV SECRET_KEY=change-me-in-production
ENV ALLOWED_HOSTS=*
ENV CACHE_DEFAULT=localhost:6379/0
ENV CACHE_AXES=localhost:6379/0

# Expose ports: 9000 for AppAPI, 8000 for OpenZaak
EXPOSE 9000 8000

# Health check - just verify the wrapper is responding (any status is ok during init)
HEALTHCHECK --interval=30s --timeout=5s --start-period=90s --retries=3 \
    CMD curl -s http://localhost:${APP_PORT:-9000}/heartbeat | grep -q status || exit 1

ENTRYPOINT ["/usr/bin/tini", "--", "/entrypoint.sh"]
