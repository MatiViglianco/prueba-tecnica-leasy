# syntax=docker/dockerfile:1

# ---------------------------------------------------------------------------
# Stage 1: build the static bundle.
# ---------------------------------------------------------------------------
FROM node:22-alpine AS build

WORKDIR /app

# Lockfile first so `npm ci` is cached until dependencies change.
COPY package.json package-lock.json ./
RUN --mount=type=cache,target=/root/.npm npm ci

COPY . .
RUN npm run build

# ---------------------------------------------------------------------------
# Stage 2: serve the bundle with nginx (non-root image, listens on 8080).
# nginx also proxies /api to the backend, so the browser sees one origin.
# ---------------------------------------------------------------------------
FROM nginxinc/nginx-unprivileged:1.27-alpine AS runtime

# Rendered at startup by the image's envsubst step with API_UPSTREAM.
COPY nginx.conf.template /etc/nginx/templates/default.conf.template
COPY --from=build /app/dist /usr/share/nginx/html

ENV API_UPSTREAM=http://backend:8000

EXPOSE 8080

HEALTHCHECK --interval=10s --timeout=3s --retries=5 \
    CMD wget -q --spider http://127.0.0.1:8080/ || exit 1
