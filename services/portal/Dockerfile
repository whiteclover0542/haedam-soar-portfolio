FROM node:22-alpine AS web
WORKDIR /web
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends iproute2 && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY backend/ ./
# -e: the app finds migrations/ and instance/ relative to its source, so it must run from /app/src.
RUN pip install --no-cache-dir -e .
COPY --from=web /web/dist ./dist
COPY entrypoint.sh /entrypoint.sh
ENV FRONTEND_DIST=/app/dist FLASK_APP=haedam_portal PYTHONUNBUFFERED=1
EXPOSE 5000
ENTRYPOINT ["sh", "/entrypoint.sh"]
