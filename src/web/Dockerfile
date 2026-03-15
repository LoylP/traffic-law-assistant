FROM node:20-alpine

WORKDIR /app

COPY src/web/package*.json /app/
RUN npm install

COPY src/web /app

EXPOSE 3000

CMD ["npm", "run", "dev", "--", "-H", "0.0.0.0", "-p", "3000"]