"""S7: make the Wazuh manager forward file-integrity alerts to Graylog (syslog UDP 5514, JSON). Safe to re-run.

python infra/wazuh/enable_s7.py
The manager's ossec.conf lives in the wazuh-etc volume, so this edits it in the running container and restarts
the manager once. Wazuh's syslog output is UDP only, so Graylog listens on a Raw UDP input (bootstrap.py).
"""
import subprocess

BLOCK = """  <!-- haedam-s7: FIM alerts to Graylog -->
  <syslog_output>
    <server>10.250.0.100</server>
    <port>5514</port>
    <format>json</format>
    <group>syscheck</group>
  </syslog_output>
</ossec_config>"""
SCRIPT = r"""
set -e
f=/var/ossec/etc/ossec.conf
if grep -q haedam-s7 "$f"; then echo already; exit 0; fi
n=$(grep -n '</ossec_config>' "$f" | head -1 | cut -d: -f1)
head -n $((n-1)) "$f" > /tmp/ossec.new; cat /tmp/s7.block >> /tmp/ossec.new; tail -n +$((n+1)) "$f" >> /tmp/ossec.new
cat /tmp/ossec.new > "$f"; rm /tmp/ossec.new /tmp/s7.block
/var/ossec/bin/wazuh-control enable client-syslog >/dev/null
/var/ossec/bin/wazuh-control restart >/dev/null
echo enabled
"""


def main():
    run = lambda *a, **k: subprocess.run(["docker", "exec", "-i", "haedam-wazuh-manager", *a], check=True, text=True, **k)
    run("sh", "-c", "cat > /tmp/s7.block", input=BLOCK)
    print(run("sh", "-c", SCRIPT, capture_output=True).stdout.strip())


if __name__ == "__main__":
    main()
