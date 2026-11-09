"""Scan files for secrets. Usage: python tools/secret_scan.py [path ...] (default: git ls-files).
Exit 1 and print `file:line: pattern` for each hit, else 0."""
import re
import subprocess
import sys
from pathlib import Path

PATTERNS = {
    "discord-webhook": re.compile(r"discord(app)?\.com/api/webhooks/\d+/"),
    "private-key": re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    # a literal value: not a function call (`=generate_password_hash(`) or attribute
    "assigned-secret": re.compile(r"(?i)(api[_-]?key|token|secret|password)\w*\s*[:=]\s*['\"]?[A-Za-z0-9/+_-]{16,}(?![\w.(])"),
}
# files that describe the patterns themselves (fixtures, plan text)
ALLOW = {"tests/test_secret_scan.py", "docs/MVP-구현계획.md"}
PLACEHOLDER =re.compile(r"(?i)change-me|replace-with|example|synthetic|e2e-only|test-|<[^>]+>|\$\{")


def files(args):
    if args:
        for a in map(Path, args):
            yield from (p for p in a.rglob("*") if p.is_file()) if a.is_dir() else [a]
    else:
        out = subprocess.run(["git", "ls-files", "-z"], capture_output=True, check=True).stdout.decode("utf-8")
        yield from (Path(p) for p in out.split("\0") if p)


def scan(paths):
    hits = []
    for path in paths:
        if path.as_posix() in ALLOW:
            continue
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except (UnicodeDecodeError, OSError):
            continue  # binary or unreadable
        for no, line in enumerate(lines, 1):
            for name, rx in PATTERNS.items():
                m = rx.search(line)
                if m and not PLACEHOLDER.search(m.group(0)):
                    hits.append(f"{path}:{no}: {name}")
    return hits


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    found = scan(files(sys.argv[1:]))
    print("\n".join(found))
    sys.exit(1 if found else 0)
