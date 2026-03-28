FROM node:20-slim

WORKDIR /app

RUN npm install -g minutes-mcp

RUN mkdir -p /data/meetings /data/inbox

VOLUME ["/data/meetings", "/data/inbox"]

EXPOSE 3100

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD node -e "require('net').createConnection({port:3100}).on('connect',()=>process.exit(0)).on('error',()=>process.exit(1))"

CMD ["minutes-mcp", "--port", "3100"]
