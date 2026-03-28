FROM node:20-slim AS mcp-server

WORKDIR /app

RUN npm install -g minutes-mcp

EXPOSE 3100

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD node -e "require('net').createConnection({port:3100}).on('connect',()=>process.exit(0)).on('error',()=>process.exit(1))"

CMD ["minutes-mcp", "--port", "3100"]

# -------------------------------------------------------------------
FROM rust:1.77-slim-bookworm AS cli-builder

RUN apt-get update && apt-get install -y --no-install-recommends \
    cmake pkg-config libssl-dev libclang-dev && \
    rm -rf /var/lib/apt/lists/*

RUN cargo install minutes-cli

# -------------------------------------------------------------------
FROM debian:bookworm-slim AS cli

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates libssl3 ffmpeg && \
    rm -rf /var/lib/apt/lists/*

COPY --from=cli-builder /usr/local/cargo/bin/minutes /usr/local/bin/minutes

RUN mkdir -p /data/meetings /data/inbox

VOLUME ["/data/meetings", "/data/inbox"]

ENTRYPOINT ["minutes"]
CMD ["watch"]
