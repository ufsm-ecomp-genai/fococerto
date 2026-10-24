# FocoCerto: one image with the Python app and the optional H-MEM service (Node 24).
# Default command = sample mode (no Zetaris, Nightshift or keys needed):
#   docker build -t fococerto .
#   docker run --rm fococerto
# Real mode: docker run --rm --env-file .env fococerto run --regiao tocantins --recursos cenarios/tocantins-escasso.yaml
# (inside the container use host.docker.internal to reach Zetaris, Nightshift and Postgres on the host)
FROM node:24-bookworm-slim AS node

FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1
WORKDIR /app

# Node runtime for services/hmem (optional: `docker run ... --entrypoint npm fococerto --prefix services/hmem start`)
COPY --from=node /usr/local/bin/node /usr/local/bin/node
COPY --from=node /usr/local/lib/node_modules /usr/local/lib/node_modules
RUN ln -s /usr/local/lib/node_modules/npm/bin/npm-cli.js /usr/local/bin/npm \
 && ln -s /usr/local/lib/node_modules/npm/bin/npx-cli.js /usr/local/bin/npx

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY services/hmem/package.json services/hmem/package-lock.json services/hmem/
RUN cd services/hmem && npm ci --no-audit --no-fund

COPY . .
RUN mkdir -p logs out data/estado

ENTRYPOINT ["python", "-m", "app.cli"]
CMD ["run", "--sample", "--regiao", "tocantins", "--recursos", "cenarios/tocantins-escasso.yaml"]
