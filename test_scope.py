"""Unit tests for the central scope guardrail (scope.py).

Pure standard-library unittest: no network, no lab, no external tools. Run with:
    python3 -m unittest test_scope -v
"""

import os
import tempfile
import unittest

from scope import load_scope, is_in_scope


def _networks(*entries):
    """Build a scope from raw lines via a temp file (exercises load_scope)."""
    fd, path = tempfile.mkstemp(suffix=".txt")
    try:
        with os.fdopen(fd, "w") as f:
            f.write("\n".join(entries) + "\n")
        return load_scope(path)
    finally:
        os.unlink(path)


class IsInScope(unittest.TestCase):
    def test_single_ip_in_scope(self):
        nets = _networks("192.168.56.10")
        self.assertTrue(is_in_scope("192.168.56.10", nets))

    def test_ip_out_of_scope(self):
        nets = _networks("192.168.56.10")
        self.assertFalse(is_in_scope("192.168.56.11", nets))

    def test_cidr_covers_range(self):
        nets = _networks("10.0.0.0/24")
        self.assertTrue(is_in_scope("10.0.0.200", nets))
        self.assertFalse(is_in_scope("10.0.1.1", nets))

    def test_hostname_is_rejected(self):
        # Targets must be IPs; a hostname is never in scope.
        nets = _networks("192.168.56.10")
        self.assertFalse(is_in_scope("example.com", nets))

    def test_garbage_target_is_rejected(self):
        nets = _networks("192.168.56.10")
        self.assertFalse(is_in_scope("not-an-ip", nets))

    def test_empty_scope_allows_nothing(self):
        self.assertFalse(is_in_scope("192.168.56.10", []))


class LoadScope(unittest.TestCase):
    def test_comments_and_blanks_ignored(self):
        nets = _networks("# a comment", "", "   ", "192.168.56.10")
        self.assertEqual(len(nets), 1)
        self.assertTrue(is_in_scope("192.168.56.10", nets))

    def test_malformed_line_is_skipped_not_fatal(self):
        # A bad entry must not crash the load; the valid ones still load.
        nets = _networks("192.168.56.10", "not-a-network", "10.0.0.0/99", "10.0.0.0/24")
        self.assertTrue(is_in_scope("192.168.56.10", nets))
        self.assertTrue(is_in_scope("10.0.0.5", nets))
        self.assertEqual(len(nets), 2)

    def test_multiple_entries(self):
        nets = _networks("192.168.56.10", "10.0.0.0/24")
        self.assertTrue(is_in_scope("192.168.56.10", nets))
        self.assertTrue(is_in_scope("10.0.0.1", nets))
        self.assertFalse(is_in_scope("172.16.0.1", nets))


if __name__ == "__main__":
    unittest.main()
