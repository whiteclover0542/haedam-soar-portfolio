"""Build step: make the Wazuh agent watch the served web files in real time (S7 FIM)."""
p = "/var/ossec/etc/ossec.conf"
s = open(p).read()
line = '  <directories realtime="yes" check_all="yes">/app/dist</directories>\n  </syscheck>'
assert "</syscheck>" in s
open(p, "w").write(s.replace("</syscheck>", line, 1))
