"""Targeted enumeration: runs nmap vulnerability scripts on one port.
Refuses any target outside the declared scope."""

import subprocess

from scope import load_scope, is_in_scope


def run_enum(target, port, scope_file):
    port = "".join(ch for ch in str(port) if ch.isdigit())
    if not port:
        return None
    if not is_in_scope(target, load_scope(scope_file)):
        return None
    try:
        result = subprocess.run(
            ["nmap", "-Pn", "-sV", "--script", "vuln", "--script-timeout", "30s", "-p", port, target],
            capture_output=True,
            text=True,
            timeout=150,
        )
        return result.stdout
    except subprocess.TimeoutExpired:
        return f"enum on port {port} stopped after 150s (scan too slow)."
