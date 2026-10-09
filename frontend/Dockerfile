FROM nginx:stable-alpine
COPY deploy/nginx.conf /etc/nginx/conf.d/default.conf
COPY frontend/dist/build/h5 /usr/share/nginx/html
EXPOSE 80
