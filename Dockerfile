# wirewright — declarative schematic engine, containerised.
#
# Build:  docker build -t wirewright .
# Use:    docker run --rm -v "$PWD":/work wirewright render /work/schematic.json -o /work/out.png
#         docker run --rm -v "$PWD":/work wirewright validate /work/schematic.json --json
#         docker run --rm wirewright components
# MCP:    docker run --rm -i wirewright-mcp     (see docker-compose.yml / README)
FROM python:3.12-slim AS base

# DejaVu fonts are required for text rendering (labels, pin names, legend).
RUN apt-get update \
    && apt-get install -y --no-install-recommends fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY pyproject.toml README.md ./
COPY src ./src
COPY schema ./schema
COPY examples ./examples

# Install the package + the MCP extra so both entry points work in the image.
RUN pip install --no-cache-dir '.[mcp]'

# Run as non-root; /work is the mount point for user contracts + outputs.
RUN useradd -m runner && mkdir -p /work && chown runner:runner /work
USER runner
WORKDIR /work

ENTRYPOINT ["wirewright"]
CMD ["--help"]
