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


# Windows-aware SMB enumeration. On a modern host SMB (139/445) is usually the
# only real attack surface, so pull the facts that drive the next decision:
# the exact OS/hostname/domain, whether SMB signing is enforced (relay risk),
# what shares and sessions are exposed, and the classic smb-vuln-* checks (a
# patched host simply reports "not vulnerable" — the methodology still runs).
SMB_SCRIPTS = (
    "smb-os-discovery,smb-security-mode,smb2-security-mode,"
    "smb-enum-shares,smb-enum-sessions,smb-vuln-ms17-010"
)


def run_smb_enum(target, scope_file):
    """Run the Windows/SMB NSE script set against 139/445. Returns raw nmap
    stdout, or None if the target is out of scope."""
    if not is_in_scope(target, load_scope(scope_file)):
        return None
    try:
        result = subprocess.run(
            ["nmap", "-Pn", "-p", "139,445", "--script", SMB_SCRIPTS,
             "--script-timeout", "40s", target],
            capture_output=True,
            text=True,
            timeout=240,
        )
        return result.stdout
    except subprocess.TimeoutExpired:
        return "smb enumeration stopped after 240s (scan too slow)."
