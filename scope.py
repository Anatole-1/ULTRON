#!/usr/bin/env python3
"""
Scope verification — the project's central safeguard.
The agent must NEVER act on a target outside the declared scope (the rules
of engagement). This module is the gatekeeper: every tool checks a target
here before touching it.
"""

import ipaddress


def load_scope(path):
    """Read the scope file and return the list of allowed networks.

    One entry per line: a single IP (192.168.1.50) or a CIDR range
    (192.168.1.0/24). Blank lines and lines starting with # are ignored.
    """
    allowed = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            allowed.append(ipaddress.ip_network(line, strict=False))
    return allowed


def is_in_scope(target, allowed):
    """Return True if the target IP belongs to one of the allowed networks."""
    ip = ipaddress.ip_address(target)
    return any(ip in network for network in allowed)


# Quick self-test when run directly: python3 scope.py
if __name__ == "__main__":
    allowed = load_scope("scope.txt")
    print("[*] Allowed scope:")
    for network in allowed:
        print(f"    - {network}")

    print("\n[*] Tests:")
    for target in ["192.168.1.50", "192.168.1.99", "8.8.8.8"]:
        verdict = "IN scope" if is_in_scope(target, allowed) else "OUT of scope (BLOCKED)"
        print(f"    {target:<15} -> {verdict}")
