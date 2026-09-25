#!/usr/bin/env python3
"""Scan the tracked working tree for secret-shaped strings.

Reports file and line, never the matched value: a scanner that echoes what it
found copies the secret into CI logs, terminal scrollback and agent
transcripts — the exact places the audit is meant to keep it out of.

Only files known to git are scanned. Gitignored files cannot leak by
publishing the repo, and scanning them produces noise that trains everyone to
ignore the gate.

Exit code 0 = clean, 1 = findings, 2 = usage/environment error.

Usage:
    python scripts/check_secrets.py [--root PATH]
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Patterns. Two families: vendor prefixes (high confidence, specific shape) and
# generic assignments (lower confidence, needs a long literal to fire).
# ---------------------------------------------------------------------------

VENDOR_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("aws-access-key-id", re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b")),
    ("github-token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{36,}\b")),
    ("openai-key", re.compile(r"\bsk-(?:proj-)?[A-Za-z0-9_-]{32,}\b")),
    ("anthropic-key", re.compile(r"\bsk-ant-[A-Za-z0-9_-]{32,}\b")),
    ("google-api-key", re.compile(r"\bAIza[0-9A-Za-z_-]{35}\b")),
    ("slack-token", re.compile(r"\bxox[abprs]-[0-9A-Za-z-]{10,}\b")),
    ("stripe-key", re.compile(r"\b[sr]k_(?:live|test)_[0-9A-Za-z]{24,}\b")),
    ("private-key-block", re.compile(r"-----BEGIN (?:[A-Z ]+ )?PRIVATE KEY-----")),
    ("jwt", re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b")),
    ("url-with-credentials", re.compile(r"\b[a-z][a-z0-9+.-]*://[^\s:/@]+:[^\s:/@]+@")),
]

# Generic `NAME = "long-literal"`. The literal must be long enough and not look
# like prose, a placeholder or an env-var reference.
_SECRET_NAME = r"(?:api[_-]?key|api[_-]?token|access[_-]?token|auth[_-]?token|secret|password|passwd|pwd|client[_-]?secret|private[_-]?key)"
GENERIC_PATTERN = re.compile(
    rf"(?i)\b{_SECRET_NAME}\b\s*[:=]\s*[\"']([^\"'\n]{{16,}})[\"']"
)

# Values that are obviously not credentials.
PLACEHOLDER = re.compile(
    r"(?i)^(?:|x{3,}|\*{3,}|\.{3,}|<.*>|\$\{.*\}|%\(.*\)s|\{\{.*\}\}|"
    r"(?:your|my|the)[_-]?.*|.*(?:example|placeholder|dummy|sample|"
    r"not[_-]?real|fake|redacted|changeme|todo|xxx|test[_-]?token|"
    r"from[_-]?the[_-]?environment).*)$"
)

# Files that are local-only config by convention and must never be tracked.
FORBIDDEN_TRACKED = re.compile(
    r"(?:^|/)(?:\.env(?:\.[^/]*)?|credentials.*\.json|ib_gateway\.conf|"
    r"id_rsa|id_ed25519|.*\.(?:key|pem|p12|pfx|keystore|jks))$"
)
FORBIDDEN_ALLOW = re.compile(r"(?:^|/)\.env\.example$")

BINARY_SUFFIXES = {
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".ico", ".pdf", ".zip", ".gz",
    ".woff", ".woff2", ".ttf", ".otf", ".duckdb", ".parquet", ".so", ".dylib",
}

MAX_BYTES = 2_000_000

# A file whose first 20 lines carry this marker is skipped. It exists for the
# probe, which must contain secret-shaped strings to prove the scanner fires.
# The marker is checked near the top only, so a real secret cannot smuggle
# itself in by appending the string further down.
IGNORE_MARKER = "check-secrets: ignore-file"


def tracked_files(root: Path) -> list[Path]:
    out = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=root, capture_output=True, text=True, check=True,
    ).stdout
    return [root / p for p in out.split("\0") if p]


def scan_line(line: str) -> list[str]:
    hits = [name for name, pat in VENDOR_PATTERNS if pat.search(line)]
    for m in GENERIC_PATTERN.finditer(line):
        value = m.group(1)
        if PLACEHOLDER.match(value):
            continue
        # An env-var indirection is the correct pattern, not a finding.
        if value.startswith("$") or "os.environ" in line or "getenv" in line:
            continue
        hits.append("generic-secret-assignment")
    return hits


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", default=".", type=Path)
    args = ap.parse_args()
    root = args.root.resolve()

    try:
        files = tracked_files(root)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("check-secrets: not a git repository (or git unavailable)", file=sys.stderr)
        return 2

    findings: list[str] = []

    for path in files:
        rel = path.relative_to(root).as_posix()

        if FORBIDDEN_TRACKED.search(rel) and not FORBIDDEN_ALLOW.search(rel):
            findings.append(f"{rel}: local-only credential file is tracked by git")
            continue

        if path.suffix.lower() in BINARY_SUFFIXES:
            continue
        if not path.is_file():
            continue
        try:
            if path.stat().st_size > MAX_BYTES:
                continue
            text = path.read_text(encoding="utf-8", errors="strict")
        except (OSError, UnicodeDecodeError):
            continue  # binary or unreadable — nothing text-shaped to leak

        lines = text.splitlines()
        if any(IGNORE_MARKER in line for line in lines[:20]):
            continue

        for lineno, line in enumerate(lines, start=1):
            for kind in scan_line(line):
                findings.append(f"{rel}:{lineno}: {kind}")

    if findings:
        print(f"check-secrets: {len(findings)} finding(s) — value not shown by design\n")
        for f in findings:
            print(f"  {f}")
        print("\nRotate the credential first if it is real, then remove it from the tree AND history.")
        return 1

    print(f"check-secrets: clean ({len(files)} tracked files scanned)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
