"""
Laya — Autonomous Voice Desktop Assistant
Local-first, low-latency PC automation and reasoning agent.
"""

import socket

# Force IPv4 resolution to eliminate Windows IPv6 DNS getaddrinfo timeouts/hangs
try:
    _orig_getaddrinfo = socket.getaddrinfo
    def _ipv4_getaddrinfo(host, port, family=0, type=0, proto=0, flags=0):
        if family == 0:
            family = socket.AF_INET
        return _orig_getaddrinfo(host, port, family, type, proto, flags)
    socket.getaddrinfo = _ipv4_getaddrinfo
except Exception:
    pass

__version__ = "1.0.0"
