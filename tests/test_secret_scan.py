import subprocess
import sys
from pathlib import Path

SCAN = Path(__file__).resolve().parents[1] / "tools" / "secret_scan.py"


def run(tmp_path, text):
    f = tmp_path / "sample.txt"
    f.write_text(text, encoding="utf-8")
    return subprocess.run([sys.executable, str(SCAN), str(f)], capture_output=True, text=True)


def test_flags_discord_webhook(tmp_path):
    r = run(tmp_path, "url = https://discord.com/api/webhooks/123/abc\n")
    assert r.returncode == 1
    assert "sample.txt:1:" in r.stdout


def test_flags_private_key(tmp_path):
    assert run(tmp_path, "-----BEGIN OPENSSH PRIVATE KEY-----\n").returncode == 1


def test_flags_assigned_token(tmp_path):
    assert run(tmp_path, 'api_key = "A1b2C3d4E5f6G7h8I9j0"\n').returncode == 1


def test_allows_placeholder(tmp_path):
    assert run(tmp_path, "GRAYLOG_PASSWORD_SECRET=change-me-to-a-long-random-string\n").returncode == 0


def test_allows_function_call_value(tmp_path):
    assert run(tmp_path, "u.password_hash=generate_password_hash(new)\n").returncode == 0


def test_allows_synthetic_test_literal(tmp_path):
    assert run(tmp_path, 'PASSWORD = "Synthetic-test-password-123"\n').returncode == 0
