FROM node:22-slim

WORKDIR /app

COPY frontend-rework-autopsy/package*.json ./
RUN npm ci

COPY frontend-rework-autopsy ./

ARG NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
ENV NEXT_PUBLIC_API_BASE_URL=$NEXT_PUBLIC_API_BASE_URL

RUN npm run build

RUN chown -R node:node /app
USER node

EXPOSE 3000

CMD ["npm", "run", "start", "--", "-H", "0.0.0.0"]
