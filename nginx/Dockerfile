FROM nginx:latest

# 기존 nginx.conf 제거
RUN rm /etc/nginx/conf.d/default.conf

# 새로운 nginx.conf 복사
COPY nginx.conf /etc/nginx/conf.d
