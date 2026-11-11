"""Inspect authenticated local pfSense form contracts without printing credentials."""

import http.cookiejar
import re
import ssl
import urllib.parse
import urllib.request


BASE = "https://127.0.0.1:8443/"


def csrf(page: str) -> str:
    match = re.search(r'name=["\']__csrf_magic["\']\s+value=["\']([^"\']+)', page)
    if not match:
        raise RuntimeError("pfSense CSRF token was not found")
    return match.group(1)


def main() -> None:
    opener = urllib.request.build_opener(
        urllib.request.HTTPSHandler(context=ssl._create_unverified_context()),
        urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()),
    )
    login = opener.open(BASE, timeout=15).read().decode()
    data = urllib.parse.urlencode({
        "__csrf_magic": csrf(login), "usernamefld": "admin", "passwordfld": "pfsense", "login": "Sign In"
    }).encode()
    response = opener.open(BASE, data, timeout=15)
    landing = response.read().decode(errors="replace")
    if "pfSense - Login" in landing:
        raise RuntimeError("pfSense default login was rejected")
    for path in ("interfaces.php?if=wan", "firewall_nat.php", "firewall_nat_edit.php", "diag_backup.php"):
        try:
            page = opener.open(urllib.parse.urljoin(BASE, path), timeout=15).read().decode(errors="replace")
            fields = re.findall(r'<(?:input|select|textarea)[^>]+(?:name|id)=["\']([^"\']+)', page)
            print(path, ",".join(fields[:80]))
            if path == "firewall_nat.php":
                print("portal-nat-rule", "10.250.0.2" in page and "5000" in page)
            if path == "firewall_nat_edit.php":
                for name in ("interface", "dstbeginport", "dstendport", "localbeginport", "filter-rule-association"):
                    match = re.search(rf'<select[^>]+name=["\']{name}["\'][^>]*>(.*?)</select>', page, re.S)
                    if match:
                        print(name, re.findall(r'<option value=["\']([^"\']+)', match.group(1))[:12])
            if path == "diag_backup.php":
                print("backup-links", [link for link in re.findall(r'href=["\']([^"\']+)', page) if "backup" in link or "download" in link])
                print("backup-buttons", re.findall(r'<(?:input|button)[^>]+(?:name|value)=[^>]+>', page))
                for name in ("backuparea", "restorearea"):
                    match = re.search(rf'<select[^>]+name=["\']{name}["\'][^>]*>(.*?)</select>', page, re.S)
                    if match:
                        print(name, re.findall(r'<option value=["\']([^"\']+)', match.group(1)))
        except urllib.error.HTTPError as error:
            print(path, error.code)


if __name__ == "__main__":
    main()
