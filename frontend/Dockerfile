# build env
FROM node:21.7.1-alpine as build
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . ./
RUN npm run build

RUN npm install --global http-server

CMD ["npx", "-y", "http-server", "-p", "7000", "/app/build"]