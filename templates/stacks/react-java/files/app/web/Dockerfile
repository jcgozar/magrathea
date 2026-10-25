# Pinned tags, non-root runtime (standards K8S-005 and K8S-006).
FROM node:22.11.0-alpine AS build
WORKDIR /src
COPY package.json package-lock.json* ./
RUN npm install
COPY . .
RUN npm run build

FROM nginxinc/nginx-unprivileged:1.27.2-alpine
COPY --from=build /src/dist /usr/share/nginx/html
EXPOSE 8080
