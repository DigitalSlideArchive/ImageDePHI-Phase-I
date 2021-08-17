FROM node:14-slim as builder
WORKDIR /code
COPY package.json \
    package-lock.json \
    /code/
RUN npm ci
COPY vite.config.ts \
    index.html \
    postcss.config.js \
    tsconfig.json \
    /code/
COPY src /code/src/
COPY public /code/public/
RUN npm run build

FROM nginx
COPY --from=builder /code/public/ /usr/share/nginx/html/
COPY nginx.conf /etc/nginx/templates/nginx.conf.template
ENV BACKEND_HOST=http://example.com \
    NGINX_ENVSUBST_OUTPUT_DIR=/etc/nginx
EXPOSE 8080
