FROM nginx:latest

RUN rm /etc/nginx/nginx.conf
COPY local.conf /etc/nginx/nginx.conf

COPY common.crt /etc/nginx/common.crt
COPY common.key /etc/nginx/common.key

EXPOSE 80

