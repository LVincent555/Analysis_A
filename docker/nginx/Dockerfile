# ==========================================
# Stage 1: 构建前端
# ==========================================
FROM node:18-alpine AS frontend-builder

WORKDIR /app

# 复制前端源码
COPY frontend/package*.json ./
RUN npm install

COPY frontend/ ./
RUN npm run build

# ==========================================
# Stage 2: Nginx服务器
# ==========================================
FROM nginx:alpine

# 复制前端构建产物
COPY --from=frontend-builder /app/build /usr/share/nginx/html

# 复制Nginx配置
COPY docker/nginx/nginx.conf /etc/nginx/nginx.conf
COPY docker/nginx/default.conf /etc/nginx/conf.d/default.conf

# 创建日志目录
RUN mkdir -p /var/log/nginx

# 暴露端口
EXPOSE 80

# 健康检查
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD wget --quiet --tries=1 --spider http://localhost:80 || exit 1

CMD ["nginx", "-g", "daemon off;"]
