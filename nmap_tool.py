#!/usr/bin/env python3
"""
nmap tool — the agent's first real capability (reconnaissance).
Every scan goes through the scope check first: an out-of-scope target is refused.
"""

import subprocess
import sys
from scope import load_scope, is_in_scope

SCOPE_FILE = "scope.txt"


def run_nmap(target):
    allowed = load_scope(SCOPE_FILE)

    if not is_in_scope(target, allowed):
        print(f"[!] REFUSED: {target} is NOT in scope. No scan performed.")
        return None

    print(f"[*] Target {target} is in scope. Running nmap...")
    result = subprocess.run(
        ["nmap", "-sV", "-F", target],
        capture_output=True,
        text=True,
    )
    return result.stdout


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python3 nmap_tool.py <target-ip>")
        sys.exit(1)

    output = run_nmap(sys.argv[1])
    if output:
        print(output)
