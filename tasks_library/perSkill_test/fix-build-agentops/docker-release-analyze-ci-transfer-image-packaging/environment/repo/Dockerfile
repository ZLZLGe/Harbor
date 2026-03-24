FROM python:3.11-slim

WORKDIR /opt/harbor
COPY src/app/ /opt/harbor/app/
COPY packaging/assets/ /opt/harbor/release/
RUN chmod +x /opt/harbor/release/entrypoint.sh
