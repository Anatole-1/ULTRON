"""nmap reconnaissance tool. Refuses any target outside the declared scope."""

import subprocess

from scope import load_scope, is_in_scope


def run_nmap(target, scope_file):
    if not is_in_scope(target, load_scope(scope_file)):
        return None
    result = subprocess.run(
        ["nmap", "-sV", "-F", target],
        capture_output=True,
        text=True,
    )
    return result.stdout
