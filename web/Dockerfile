FROM node:22-bookworm-slim AS frontend
WORKDIR /build
COPY web/app/package*.json ./
RUN npm ci --no-audit --no-fund
COPY web/app/ ./
RUN npm run build

FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 LLM_PROVIDER=offline
WORKDIR /app
COPY pyproject.toml ./
COPY app/ ./app/
RUN pip install --no-cache-dir .
COPY config/ ./config/
COPY data/cache/ ./data/cache/
COPY cenarios/ ./cenarios/
COPY input_examples/ ./input_examples/
COPY output_examples/ ./output_examples/
COPY web/api.yaml ./web/api.yaml
COPY --from=frontend /dist/ ./web/dist/
RUN mkdir -p logs out data/estado
EXPOSE 8000
CMD ["uvicorn", "app.api:app", "--host", "0.0.0.0", "--port", "8000"]
