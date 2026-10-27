FROM python:3.12-alpine
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 APP_MODE=demo BIND_HOST=0.0.0.0 ALLOW_CONTAINER_BIND=yes PORT=8091
WORKDIR /srv
RUN addgroup -S app && adduser -S app -G app && mkdir -p /data && chown app:app /data
COPY backend /srv/backend
USER app
EXPOSE 8091
HEALTHCHECK --interval=20s --timeout=5s --start-period=5s CMD python -c 'import urllib.request; urllib.request.urlopen("http://127.0.0.1:8091/api/ready",timeout=3)' || exit 1
CMD ["python", "-m", "backend.local_server"]
