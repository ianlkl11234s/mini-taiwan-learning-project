# ===== Stage 1: Build =====
FROM node:20-alpine AS build

WORKDIR /app

# 先複製 dependency 定義（利用 Docker cache）
COPY package.json package-lock.json ./
RUN npm ci

# 複製原始碼並 build
COPY . .

# Build 時需要的環境變數由 --build-arg 傳入
ARG VITE_MAPBOX_TOKEN
ARG VITE_SUPABASE_URL
ARG VITE_SUPABASE_ANON_KEY
RUN npm run build

# ===== Stage 2: Serve =====
FROM nginx:alpine

# 從 build stage 複製靜態檔案
COPY --from=build /app/dist /usr/share/nginx/html

# SPA fallback: 所有路徑都導向 index.html
RUN printf 'server {\n  listen 8080;\n  root /usr/share/nginx/html;\n  location / {\n    try_files $uri $uri/ /index.html;\n  }\n}\n' > /etc/nginx/conf.d/default.conf

EXPOSE 8080
CMD ["nginx", "-g", "daemon off;"]
