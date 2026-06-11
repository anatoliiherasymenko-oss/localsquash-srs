# Бонус: контейнеризація LocalSquash API (самостійна робота ОПІ, варіант 2)
FROM node:22-alpine

WORKDIR /app

# Спершу залежності — шар кешується, поки package*.json незмінні
COPY package*.json ./
RUN npm ci --omit=dev

COPY . .

ENV PORT=3000
EXPOSE 3000

CMD ["node", "server.js"]
