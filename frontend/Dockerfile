# Optional original React frontend. Requires Firebase configuration for full auth.
FROM node:22-alpine AS builder
WORKDIR /src
COPY package.json package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY . .
# Explicit demo-build mode: do not embed or connect to the upstream Firebase project.
ARG VITE_USE_FIREBASE_EMULATORS=true
ENV VITE_USE_FIREBASE_EMULATORS=${VITE_USE_FIREBASE_EMULATORS}
RUN npm run build

FROM nginx:1.27-alpine
COPY --from=builder /src/dist /usr/share/nginx/html
EXPOSE 80
HEALTHCHECK --interval=30s --timeout=3s CMD wget -q -O /dev/null http://127.0.0.1/ || exit 1
CMD ["nginx", "-g", "daemon off;"]
