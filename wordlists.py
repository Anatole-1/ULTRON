"""Named password-wordlist presets, shared by the online attack (hydra) and the
offline crack (john).

The lab default (`builtin`) stays small, fast and deterministic. The operator
can opt into realistic lists with `--wordlist common|rockyou`. Everything stays
bounded: hydra password lists are capped to the top N entries, and a gzipped
rockyou is decompressed once into a cache instead of on every run.

A single active level is configured once (set_active) from the CLI and read by
the tools by default, so the flag reaches both the LLM loop and the --fast
playbook without being threaded through every call site.
"""

import gzip
import os
import shutil
import tempfile

# Built-in lab-grade credentials (the historical default). Small on purpose so
# a --fast run stays quick and predictable.
BUILTIN_USERS = ["msfadmin", "user", "admin", "root", "service", "postgres"]
BUILTIN_PASSWORDS = ["msfadmin", "user", "admin", "password", "root", "toor",
                     "postgres", "123456"]

# A modest, curated set of usernames for the bigger levels. Kept short on
# purpose: online cost is users x passwords, so we grow passwords, not users.
COMMON_USERS = BUILTIN_USERS + ["administrator", "guest", "test", "oracle",
                                "ftp", "mysql", "www-data", "ubuntu"]

# Candidate on-disk password lists per level, best first; the first that exists
# wins. common -> John's bundled list; rockyou -> the classic leak (often .gz).
_PASSWORD_FILES = {
    "common": ["/usr/share/john/password.lst",
               "/usr/share/wordlists/john.lst",
               "/usr/share/nmap/nselib/data/passwords.lst"],
    "rockyou": ["/usr/share/wordlists/rockyou.txt",
                "/usr/share/wordlists/rockyou.txt.gz"],
}

LEVELS = ["builtin", "common", "rockyou"]

# Default cap on how many passwords hydra tries online. rockyou has ~14M lines;
# replaying all of them over the network is neither fast nor polite, so we take
# the top N (rockyou is ordered most-common first).
HYDRA_MAX_PASSWORDS = 2000

_CACHE_DIR = os.path.join(tempfile.gettempdir(), "ultron-wordlists")

_ACTIVE = "builtin"


def set_active(level):
    """Set the active level (used when a tool is called with level=None)."""
    global _ACTIVE
    _ACTIVE = level if level in LEVELS else "builtin"
    return _ACTIVE


def active():
    return _ACTIVE


def _first_existing(paths):
    for p in paths:
        if os.path.exists(p):
            return p
    return None


def _ensure_plaintext(path):
    """Return a plaintext wordlist path, decompressing a .gz once into a cache.
    Returns None if nothing usable."""
    if path is None:
        return None
    if not path.endswith(".gz"):
        return path
    try:
        os.makedirs(_CACHE_DIR, exist_ok=True)
        out = os.path.join(_CACHE_DIR, os.path.basename(path)[:-3])
        if os.path.exists(out) and os.path.getsize(out) > 0:
            return out
        tmp = out + ".partial"
        with gzip.open(path, "rt", errors="ignore") as src, open(tmp, "w") as dst:
            shutil.copyfileobj(src, dst)
        os.replace(tmp, out)  # atomic: a crashed decompress never looks complete
        return out
    except OSError:
        return None


def _capped_copy(path, max_lines):
    """Return a path to the first max_lines of `path`, cached by (name, N). Keeps
    hydra from being handed a multi-million-line file."""
    if path is None:
        return None
    try:
        os.makedirs(_CACHE_DIR, exist_ok=True)
        out = os.path.join(_CACHE_DIR, f"{os.path.basename(path)}.top{max_lines}")
        if os.path.exists(out) and os.path.getsize(out) > 0:
            return out
        tmp = out + ".partial"
        with open(path, "r", errors="ignore") as src, open(tmp, "w") as dst:
            for i, line in enumerate(src):
                if i >= max_lines:
                    break
                dst.write(line)
        os.replace(tmp, out)
        return out
    except OSError:
        return None


def hydra_users(level=None):
    """Usernames for an online attack at `level`."""
    level = level or _ACTIVE
    return COMMON_USERS if level in ("common", "rockyou") else BUILTIN_USERS


def hydra_password_file(level=None, max_passwords=HYDRA_MAX_PASSWORDS):
    """Path to a capped password file for hydra -P, or None to tell the caller to
    fall back to the built-in in-memory password list."""
    level = level or _ACTIVE
    if level == "builtin":
        return None
    path = _ensure_plaintext(_first_existing(_PASSWORD_FILES.get(level, [])))
    if path is None:
        return None
    return _capped_copy(path, max_passwords)


def crack_wordlist(level=None):
    """Wordlist for john. Offline cracking is time-bounded (not count-bounded),
    so rockyou is handed over in full. Builtin/common use John's bundled list."""
    level = level or _ACTIVE
    john_default = "/usr/share/john/password.lst"
    if level == "rockyou":
        rock = _ensure_plaintext(_first_existing(_PASSWORD_FILES["rockyou"]))
        if rock:
            return rock
    return _first_existing([john_default, "/usr/share/wordlists/john.lst"]) or john_default
