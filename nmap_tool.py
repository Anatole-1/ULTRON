"""nmap reconnaissance tool. Refuses any target outside the declared scope."""

import subprocess

from scope import load_scope, is_in_scope


def run_nmap(target, scope_file):
    if not is_in_scope(target, load_scope(scope_file)):
        return None
    # -Pn: skip host discovery. Lab targets often drop ICMP (and without root
    # nmap can't fall back to ARP), which would wrongly mark them "down" and
    # scan nothing. The target is already scope-gated, so we scan it regardless.
    result = subprocess.run(
        ["nmap", "-Pn", "-sV", "-F", target],
        capture_output=True,
        text=True,
    )
    return result.stdout
