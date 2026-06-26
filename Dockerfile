FROM node:20-slim AS dashboard-build

WORKDIR /workspace/dashboard
COPY dashboard/package*.json ./
RUN npm ci
COPY dashboard ./
RUN npm run build

FROM python:3.10-slim

ENV PYTHONUNBUFFERED=1
ENV APP_HOME=/workspace

WORKDIR ${APP_HOME}

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY backend ./backend
COPY --from=dashboard-build /workspace/dashboard/dist ./dashboard/dist
COPY tools ./tools
COPY Makefile README.md ./

EXPOSE 8000

CMD ["python3", "backend/server.py"]
