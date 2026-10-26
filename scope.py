"""Scope verification: the agent only acts on targets listed in the scope file."""

import ipaddress


def load_scope(path):
    networks = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                networks.append(ipaddress.ip_network(line, strict=False))
    return networks


def is_in_scope(target, networks):
    try:
        ip = ipaddress.ip_address(target)
    except ValueError:
        return False
    return any(ip in net for net in networks)
