"""Online credential attack (hydra) against ONE service of an in-scope target.
Bounded to a small built-in list of common weak credentials (lab-grade), so the
run stays fast and predictable. Scope-gated like every other tool."""

import os
import subprocess
import tempfile

import wordlists
from scope import load_scope, is_in_scope

# Per-service hydra timeout in seconds. telnet negotiates slowly and can hang,
# so we cap it low (fail fast, move on) instead of wasting the default budget.
DEFAULT_TIMEOUT = 180
SERVICE_TIMEOUTS = {"telnet": 45}


def _timeout_for(service):
    return SERVICE_TIMEOUTS.get(service, DEFAULT_TIMEOUT)


def run_hydra(target, service, scope_file, level=None):
    """Brute-force ONE auth service. The username/password lists come from the
    active wordlist level (see wordlists.set_active); `level` overrides it. The
    built-in level keeps the historical small in-memory password list; bigger
    levels hand hydra a capped on-disk file (-P) instead. Scope-gated."""
    service = "".join(ch for ch in str(service).lower() if ch.isalnum())
    if not service:
        return None
    if not is_in_scope(target, load_scope(scope_file)):
        return None

    users = wordlists.hydra_users(level)
    uf = tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False)
    uf.write("\n".join(users) + "\n")
    uf.close()

    # Bigger levels resolve to a real file on disk; builtin falls back to the
    # small in-memory list written to a temp file.
    pfile = wordlists.hydra_password_file(level)
    own_pf = pfile is None
    if own_pf:
        pf = tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False)
        pf.write("\n".join(wordlists.BUILTIN_PASSWORDS) + "\n")
        pf.close()
        pfile = pf.name

    try:
        result = subprocess.run(
            ["hydra", "-L", uf.name, "-P", pfile, "-t", "4", target, service],
            capture_output=True, text=True, timeout=_timeout_for(service),
        )
        return (result.stdout + result.stderr).strip()
    except subprocess.TimeoutExpired:
        return f"hydra on {service} timed out."
    finally:
        os.unlink(uf.name)
        if own_pf:
            os.unlink(pfile)


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
