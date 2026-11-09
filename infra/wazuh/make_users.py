"""Write infra/wazuh/config/internal_users.yml from .env (bcrypt via the indexer image's hash.sh). Output is gitignored."""
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "infra/wazuh/config"


def env():
    pairs = (l.split("=", 1) for l in (ROOT / ".env").read_text("utf-8").splitlines() if "=" in l and not l.startswith("#"))
    return {k.strip(): v.strip() for k, v in pairs}


def bcrypt(password):
    # The password goes in via the PW env var name only (value from this process's env), never on a command line.
    r = subprocess.run(["docker", "run", "--rm", "-e", "PW", "-e", "OPENSEARCH_JAVA_HOME=/usr/share/wazuh-indexer/jdk",
                        "--entrypoint", "bash", "wazuh/wazuh-indexer:4.9.2",
                        "-c", 'bash /usr/share/wazuh-indexer/plugins/opensearch-security/tools/hash.sh -p "$PW"'],
                       capture_output=True, text=True, env={**os.environ, "PW": password})
    hashes = [l for l in r.stdout.splitlines() if l.startswith("$2")]
    if r.returncode or not hashes:
        raise SystemExit(f"hash.sh failed (exit {r.returncode}); password not shown")
    return hashes[0]


def main():
    e = env()
    hashes = {"admin": bcrypt(e["WAZUH_INDEXER_PASSWORD"]), "kibanaserver": bcrypt(e["WAZUH_DASHBOARD_PASSWORD"])}
    text = (CONFIG / "internal_users.template.yml").read_text("utf-8").format(**hashes)
    (CONFIG / "internal_users.yml").write_text(text.split("\n", 1)[1], "utf-8", newline="\n")
    print("wrote infra/wazuh/config/internal_users.yml")


if __name__ == "__main__":
    main()
