"""Apply the minimal local pfSense configuration required by the MVP lab."""

import http.cookiejar
import re
import ssl
import urllib.parse
import urllib.request
import uuid
import xml.etree.ElementTree as ET
from copy import deepcopy
from pathlib import Path


BASE = "https://127.0.0.1:8443/"
ROOT = Path(__file__).resolve().parents[1]


def csrf(page: str) -> str:
    match = re.search(r'name=["\']__csrf_magic["\']\s+value=["\']([^"\']+)', page)
    if not match:
        raise RuntimeError("pfSense CSRF token was not found")
    return match.group(1)


class PfSense:
    def __init__(self) -> None:
        self.opener = urllib.request.build_opener(
            urllib.request.HTTPSHandler(context=ssl._create_unverified_context()),
            urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()),
        )

    def get(self, path: str) -> str:
        return self.opener.open(urllib.parse.urljoin(BASE, path), timeout=20).read().decode(errors="replace")

    def post(self, path: str, fields: dict[str, str]) -> str:
        data = urllib.parse.urlencode(fields).encode()
        return self.opener.open(urllib.parse.urljoin(BASE, path), data, timeout=30).read().decode(errors="replace")

    def backup(self) -> bytes:
        page = self.get("diag_backup.php")
        data = urllib.parse.urlencode({
            "__csrf_magic": csrf(page),
            "donotbackuprrd": "yes",
            "backupssh": "yes",
            "download": "Download configuration as XML",
        }).encode()
        return self.opener.open(urllib.parse.urljoin(BASE, "diag_backup.php"), data, timeout=30).read()

    def restore(self, configuration: bytes, area: str) -> str:
        page = self.get("diag_backup.php")
        boundary = f"----haedam-{uuid.uuid4().hex}"
        parts = [
            ("__csrf_magic", None, csrf(page)),
            ("restorearea", None, area),
            ("conffile", "config.xml", configuration),
            ("restore", None, "Restore Configuration"),
        ]
        body = bytearray()
        for name, filename, value in parts:
            body.extend(f"--{boundary}\r\n".encode())
            if filename:
                body.extend(f'Content-Disposition: form-data; name="{name}"; filename="{filename}"\r\n'.encode())
                body.extend(b"Content-Type: application/xml\r\n\r\n")
                body.extend(value)
            else:
                body.extend(f'Content-Disposition: form-data; name="{name}"\r\n\r\n{value}'.encode())
            body.extend(b"\r\n")
        body.extend(f"--{boundary}--\r\n".encode())
        request = urllib.request.Request(
            urllib.parse.urljoin(BASE, "diag_backup.php"),
            data=bytes(body),
            headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        )
        return self.opener.open(request, timeout=60).read().decode(errors="replace")

    def login(self) -> None:
        page = self.get("")
        landing = self.post("", {
            "__csrf_magic": csrf(page),
            "usernamefld": "admin",
            "passwordfld": "pfsense",
            "login": "Sign In",
        })
        if "pfSense - Login" in landing:
            raise RuntimeError("pfSense default login was rejected")


def main() -> None:
    pf = PfSense()
    pf.login()

    wan_page = pf.get("interfaces.php?if=wan")
    pf.post("interfaces.php?if=wan", {
        "__csrf_magic": csrf(wan_page),
        "enable": "on",
        "descr": "WAN",
        "type": "static",
        "type6": "none",
        "ipaddr": "203.0.113.1",
        "subnet": "24",
        "gateway": "none",
        "spoofmac": "",
        "mtu": "",
        "mss": "",
        "mediaopt": "",
        "ipaddrv6": "",
        "subnetv6": "",
        "gatewayv6": "none",
        "save": "Save",
    })

    live = ET.fromstring(pf.backup())
    reference = ET.parse(ROOT / "infra" / "pfsense" / "config.xml").getroot()
    wan = live.find("./interfaces/wan")
    if wan is None:
        raise RuntimeError("live pfSense WAN interface is missing")
    for tag in ("blockpriv", "blockbogons"):
        for node in wan.findall(tag):
            wan.remove(node)
    live_nat = live.find("./nat")
    live_filter = live.find("./filter")
    ref_nat = reference.find("./nat/rule")
    ref_filter = next(rule for rule in reference.findall("./filter/rule") if rule.find("associated-rule-id") is not None)
    for rule in list(live_nat.findall("rule")):
        if rule.findtext("target") == "10.250.0.2" and rule.findtext("local-port") == "5000":
            live_nat.remove(rule)
    for rule in list(live_filter.findall("rule")):
        if rule.findtext("associated-rule-id") == ref_filter.findtext("associated-rule-id"):
            live_filter.remove(rule)
    live_nat.append(deepcopy(ref_nat))
    live_filter.append(deepcopy(ref_filter))
    payload = ET.tostring(live, encoding="utf-8", xml_declaration=True)
    for area in ("interfaces", "nat", "filter"):
        restored = pf.restore(payload, area)
        if "configuration area has been restored" not in restored and "The configuration has been restored" not in restored:
            alerts = re.findall(r'<div[^>]+(?:alert|input-errors)[^>]*>(.*?)</div>', restored, re.S)
            message = " | ".join(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", item)).strip() for item in alerts)
            raise RuntimeError(f"pfSense {area} restore was not confirmed: {message or 'no status message'}")
    print("WAN filters disabled; TCP/80 -> 10.250.0.2:5000 NAT and associated rule restored")


if __name__ == "__main__":
    main()
