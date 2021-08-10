FROM node:14 AS builder
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
COPY --from=builder /code/dist/ /usr/share/nginx/html
COPY nginx.conf /etc/nginx/templates/nginx.conf.template
ENV NGINX_ENVSUBST_OUTPUT_DIR=/etc/nginx
ENV BACKEND_HOST=http://example.com
EXPOSE 8080
