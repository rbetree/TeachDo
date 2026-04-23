# Stage 1: Build the Vue/Vite app
FROM node:22-alpine AS build
WORKDIR /app

# 更快的缓存层：先只拷贝依赖清单
COPY package*.json ./

# 更可重复的安装方式
RUN npm ci

# 拷贝源代码并构建
COPY . .
RUN npm run build

# Stage 2: Serve with Nginx (unprivileged)
FROM nginxinc/nginx-unprivileged:stable-alpine
WORKDIR /usr/share/nginx/html

# 清空默认站点文件（需切回 root 才能删除 nginx 预置文件）
USER root
RUN rm -rf ./*
USER 101

# 从 build 阶段拷贝静态产物
COPY --from=build /app/dist .

# 使用自定义 Nginx 配置（同源代理 /api 到 main_api）
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Health check for the Nginx serving port
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD wget --quiet --tries=1 --spider http://localhost:8080/ || exit 1

EXPOSE 8080
CMD ["nginx", "-g", "daemon off;"]

