#!/bin/sh
set -eu
# Replies to citizens/attackers go back through pfSense, not Docker's gateway,
# so source IPs stay real. A light local demo intentionally omits pfSense.
if [ -n "${PORTAL_WAN_GATEWAY:-}" ]; then
  ip route replace 203.0.113.0/24 via "$PORTAL_WAN_GATEWAY"
fi

python - <<'EOF'
import os, time, pymysql
from urllib.parse import urlparse
u = urlparse(os.environ["DATABASE_URL"].replace("mysql+pymysql", "mysql"))
for _ in range(30):
    try:
        pymysql.connect(host=u.hostname, port=u.port or 3306, user=u.username, password=u.password,
                        database=u.path.lstrip("/"), connect_timeout=2).close()
        break
    except pymysql.MySQLError:
        time.sleep(2)
else:
    raise SystemExit("MySQL not reachable after 60s")
EOF

flask db upgrade
# Both commands refuse on a non-empty DB, so re-running on restart is a no-op.
# seed-demo prints a demo password; keep it out of docker logs.
flask seed-demo --confirm 2>&1 | grep -v '비밀번호' || true
printf '%s\n%s\n' "$PORTAL_ADMIN_PASSWORD" "$PORTAL_ADMIN_PASSWORD" |
  flask create-admin --username "$PORTAL_ADMIN_USERNAME" --name "관리자" 2>&1 | grep -v -i password || true

# S7: file integrity agent. The portal still serves if the manager (wazuh profile) is not running.
/var/ossec/bin/wazuh-control start >/dev/null 2>&1 || echo "wazuh agent not started"

exec waitress-serve --port 5000 --call haedam_portal:create_app
