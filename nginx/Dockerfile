FROM nginx:alpine

COPY nginx/nginx.conf /etc/nginx/conf.d/default.conf
COPY data/wiki /seed/data/wiki
COPY data/datasets /seed/data/datasets
COPY data/raid-bosses /seed/data/raid-bosses
RUN mkdir -p /seed/data/media

COPY nginx/docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

ENTRYPOINT ["/docker-entrypoint.sh"]
CMD ["nginx", "-g", "daemon off;"]


