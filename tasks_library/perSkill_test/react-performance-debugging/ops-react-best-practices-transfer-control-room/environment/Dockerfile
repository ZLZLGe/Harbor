FROM node:20-bookworm

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    curl \
    psmisc \
    python3 \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*

RUN pip3 install --break-system-packages pytest==8.3.4 httpx==0.28.1

WORKDIR /services/api-simulator
COPY api-simulator/package.json /services/api-simulator/package.json
COPY api-simulator/src /services/api-simulator/src
RUN npm install

WORKDIR /app
COPY website/package.json /app/package.json
COPY website/tsconfig.json /app/tsconfig.json
COPY website/next.config.js /app/next.config.js
COPY website/next-env.d.ts /app/next-env.d.ts
COPY website/src /app/src
COPY skills /root/.codex/skills
RUN npm install

ENV EXTERNAL_API_URL=http://localhost:3001

RUN printf '#!/bin/bash\ncd /services/api-simulator && npm start >/tmp/api-simulator.log 2>&1 &\nexec "$@"\n' > /usr/local/bin/entrypoint.sh \
    && chmod +x /usr/local/bin/entrypoint.sh

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
CMD ["/bin/bash"]
