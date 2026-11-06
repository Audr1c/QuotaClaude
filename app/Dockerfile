# Hub (HUB-1): the widget and the API for every device, on an always-on machine. Standard library only.
# The PCs keep doing the readings and push them here (run.py hub --url ... --token ...): no Claude token in here.
#   docker build -t claude-usage-hub .
#   docker run -d -p 8765:8765 -v claude-usage-data:/app/data claude-usage-hub
#   docker exec <container> cat /app/data/api_token        <- give this to the PCs and to your browser (/?token=...)
# Reach it through Tailscale / WireGuard, or an HTTPS reverse proxy, not straight from the Internet.
FROM python:3-alpine
WORKDIR /app
COPY . /app
RUN rm -rf /app/data && adduser -D -H tracker && mkdir /app/data && chown tracker /app/data
USER tracker
VOLUME /app/data
EXPOSE 8765
CMD ["python", "server.py", "--bind", "0.0.0.0", "--token-file", "data/api_token"]
