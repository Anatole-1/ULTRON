"""Scope verification: the agent only acts on targets listed in the scope file."""

import ipaddress
import sys


def load_scope(path):
    """Parse the scope file into a list of networks. A malformed line is skipped
    with a warning rather than crashing the whole load — one typo must not take
    the central guardrail down with it."""
    networks = []
    with open(path) as f:
        for lineno, line in enumerate(f, 1):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            try:
                networks.append(ipaddress.ip_network(line, strict=False))
            except ValueError:
                print(f"[!] scope {path}:{lineno}: ignoring invalid entry {line!r}",
                      file=sys.stderr)
    return networks


def is_in_scope(target, networks):
    try:
        ip = ipaddress.ip_address(target)
    except ValueError:
        return False
    return any(ip in net for net in networks)
