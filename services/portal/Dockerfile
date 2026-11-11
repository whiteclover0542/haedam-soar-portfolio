FROM node:22-alpine AS web
WORKDIR /web
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim
# S7: Wazuh agent watches the served files (FIM). It enrolls with the manager by itself on first start.
ARG WAZUH_VERSION=4.9.2
RUN apt-get update && apt-get install -y --no-install-recommends iproute2 curl ca-certificates procps  && curl -fsSLo /tmp/wazuh-agent.deb https://packages.wazuh.com/4.x/apt/pool/main/w/wazuh-agent/wazuh-agent_${WAZUH_VERSION}-1_amd64.deb  && WAZUH_MANAGER=10.250.0.4 WAZUH_AGENT_NAME=haedam-portal apt-get install -y --no-install-recommends /tmp/wazuh-agent.deb  && rm -rf /tmp/wazuh-agent.deb /var/lib/apt/lists/*
WORKDIR /app
COPY backend/ ./
# -e: the app finds migrations/ and instance/ relative to its source, so it must run from /app/src.
RUN pip install --no-cache-dir -e .
COPY --from=web /web/dist ./dist
# S7 restore tool (bot 117): baseline copy of the built files outside the web root, restore/quarantine via active response.
COPY s7/s7_restore.py /opt/haedam-s7/bin/s7_restore.py
COPY s7/s7-restore-ar /var/ossec/active-response/bin/s7-restore-ar
COPY s7/watch_dist.py /tmp/watch_dist.py
RUN chmod 0755 /opt/haedam-s7/bin/s7_restore.py && chown root:wazuh /var/ossec/active-response/bin/s7-restore-ar  && chmod 0750 /var/ossec/active-response/bin/s7-restore-ar  && python /opt/haedam-s7/bin/s7_restore.py baseline  && python /tmp/watch_dist.py && rm /tmp/watch_dist.py && grep -q 'realtime="yes" check_all="yes">/app/dist' /var/ossec/etc/ossec.conf
COPY entrypoint.sh /entrypoint.sh
ENV FRONTEND_DIST=/app/dist FLASK_APP=haedam_portal PYTHONUNBUFFERED=1
EXPOSE 5000
ENTRYPOINT ["sh", "/entrypoint.sh"]
