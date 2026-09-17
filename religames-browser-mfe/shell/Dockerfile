FROM node:20-alpine AS builder
WORKDIR /app
COPY package.json ./
RUN npm install --no-audit --no-fund
COPY build.mjs ./
COPY src ./src
RUN node build.mjs

FROM nginx:1.27-alpine
COPY public/ /usr/share/nginx/html/
COPY index.html.template /usr/share/nginx/templates/index.html.template
COPY --from=builder /app/dist/js/*.min.js /usr/share/nginx/html/js/
COPY --from=builder /app/dist/js/*.map /usr/share/nginx/html-internal/maps/
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY docker-entrypoint.d/40-nr-config.sh /docker-entrypoint.d/40-nr-config.sh
RUN chmod +x /docker-entrypoint.d/40-nr-config.sh

EXPOSE 80

HEALTHCHECK --interval=10s --timeout=3s --start-period=10s --retries=5 \
  CMD wget -qO- http://127.0.0.1/health || exit 1
