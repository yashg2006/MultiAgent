# Build the SPA, then serve it with nginx, which also proxies the API so the
# browser talks to a single origin (no CORS, session cookie is same-site).
FROM node:22-alpine AS build
WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm install --no-audit --no-fund
COPY . .
RUN npm run build

FROM nginx:1.27-alpine AS runtime
RUN apk add --no-cache curl
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 8080
