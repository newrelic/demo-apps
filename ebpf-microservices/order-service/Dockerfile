FROM node:24.22.1-alpine

WORKDIR /app

COPY package*.json ./

RUN npm install --production

COPY . .

ENV PORT=3002

EXPOSE 3002

CMD ["npm", "start"]
