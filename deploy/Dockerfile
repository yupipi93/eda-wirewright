# wirewright HTTP API — the image deployed to Cloud Run.
#
# POST a schematic contract, get a wiring-diagram PNG. Built from the repo root
# (build context "."), so it packages the whole `wirewright` engine.
FROM python:3.12-slim

# DejaVu fonts are required for text rendering (labels, pin names, legend).
RUN apt-get update \
    && apt-get install -y --no-install-recommends fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY pyproject.toml README.md ./
COPY src ./src

# Engine + HTTP API deps (Flask + gunicorn).
RUN pip install --no-cache-dir '.[api]'

# Cloud Run injects PORT (default 8080). Non-root for good measure.
RUN useradd -m runner
USER runner
ENV PORT=8080
EXPOSE 8080

# 2 workers × 4 threads is plenty for a stateless, CPU-light render service;
# 120 s timeout covers the largest diagrams.
CMD exec gunicorn wirewright.api:app \
    --bind "0.0.0.0:${PORT}" \
    --workers 2 --threads 4 --timeout 120 \
    --access-logfile - --error-logfile -
