FROM node:20 as build

WORKDIR /app

COPY package*.json ./
RUN npm ci

COPY tsconfig.json ./
COPY src ./src
COPY public ./public
RUN npm run build

FROM nginx:alpine

COPY --from=build /app/public /usr/share/nginx/html
