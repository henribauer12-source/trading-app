#!/usr/bin/env python3
"""Prove check_secrets.py actually fires.

A secret scanner that silently matches nothing looks identical to a clean
repo. This plants one fake secret of every shape the scanner claims to catch
into a tracked file, runs the scanner, asserts it exits non-zero and reports
caught-vs-planted per shape — then removes the file and verifies the tree is
clean again, so a failed probe cannot leave a fake-secret file behind for the
next `git add -A`.

Exit 0 = every planted shape was caught. Exit 1 = a pattern is broken.

check-secrets: ignore-file — this file carries fake secrets on purpose.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROBE = ROOT / "_leak_probe_fixture.py"

# Fake values, built so they match the shapes without being real credentials.
SHAPES: dict[str, str] = {
    "aws-access-key-id":        'AWS = "AKIA' + "IOSFODNN7EXAMPLE"[:16] + '"',
    "github-token":             'GH = "ghp_' + "0" * 36 + '"',
    "openai-key":               'OA = "sk-' + "A" * 40 + '"',
    "anthropic-key":            'AN = "sk-ant-' + "B" * 40 + '"',
    "google-api-key":           'GO = "AIza' + "C" * 35 + '"',
    "slack-token":              'SL = "xoxb-' + "1" * 20 + '"',
    "stripe-key":               'ST = "sk_live_' + "D" * 24 + '"',
    "private-key-block":        'PK = """-----BEGIN RSA PRIVATE KEY-----"""',
    "jwt":                      'JW = "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NX0.' + "E" * 20 + '"',
    "url-with-credentials":     'DB = "postgres://user:hunter2hunter2@db.internal/app"',
    "generic-secret-assignment": 'api_key = "9f83bc21ae7d40559c0e"',
}


def run_scanner() -> tuple[int, str]:
    proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "check_secrets.py"), "--root", str(ROOT)],
        capture_output=True, text=True,
    )
    return proc.returncode, proc.stdout + proc.stderr


def git(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True)


def main() -> int:
    baseline = git("status", "--porcelain").stdout.strip()

    caught: dict[str, bool] = {}
    try:
        for shape, literal in SHAPES.items():
            PROBE.write_text(f"# leak probe fixture — fake values only\n{literal}\n", encoding="utf-8")
            git("add", "-N", str(PROBE))  # make it tracked so the scanner sees it
            code, out = run_scanner()
            caught[shape] = code == 1 and shape in out
            git("rm", "--cached", "--force", "--quiet", str(PROBE))
            PROBE.unlink(missing_ok=True)
    finally:
        git("rm", "--cached", "--force", "--quiet", str(PROBE))
        PROBE.unlink(missing_ok=True)

    planted = len(caught)
    hits = sum(caught.values())
    for shape, ok in caught.items():
        print(f"  {'caught ' if ok else 'MISSED '} {shape}")
    print(f"\nleak-probe: {hits}/{planted} planted shapes caught")

    dirty = git("status", "--porcelain").stdout.strip()
    if dirty != baseline:
        print(f"leak-probe: tree changed by the probe:\n{dirty}", file=sys.stderr)
        return 1

    if hits != planted:
        print("leak-probe: a pattern is broken — fix it before trusting a clean scan", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
