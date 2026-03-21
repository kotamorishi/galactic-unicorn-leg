"""Minimal captive portal DNS server.

Responds to ALL DNS queries with the AP's own IP address.
This causes phones/laptops to detect a captive portal and
automatically open a browser to the setup page.
"""

try:
    import usocket as socket
except ImportError:
    import socket

try:
    import uasyncio as asyncio
except ImportError:
    import asyncio


class CaptiveDNS:
    """Tiny DNS server that redirects all lookups to a single IP."""

    def __init__(self, ip="192.168.4.1"):
        self._ip = ip
        self._sock = None
        self._running = False

    def _build_response(self, request):
        """Build a DNS response pointing to our IP for any query."""
        # DNS header: copy ID, set flags to "standard response, no error"
        # request[0:2] = transaction ID
        header = request[0:2]  # ID
        header += b"\x81\x80"  # Flags: response, recursion available
        header += request[4:6]  # Questions count
        header += request[4:6]  # Answers count (same as questions)
        header += b"\x00\x00"  # Authority RRs
        header += b"\x00\x00"  # Additional RRs

        # Copy the question section
        qn_end = 12
        while request[qn_end] != 0:
            qn_end += request[qn_end] + 1
        qn_end += 5  # null byte + qtype(2) + qclass(2)
        question = request[12:qn_end]

        # Answer section: pointer to name in question + A record
        answer = b"\xc0\x0c"  # Pointer to name at offset 12
        answer += b"\x00\x01"  # Type A
        answer += b"\x00\x01"  # Class IN
        answer += b"\x00\x00\x00\x3c"  # TTL 60s
        answer += b"\x00\x04"  # Data length 4
        # IP address bytes
        parts = self._ip.split(".")
        answer += bytes([int(p) for p in parts])

        return header + question + answer

    async def run(self):
        """Start the DNS server on port 53 (UDP)."""
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._sock.setblocking(False)
        self._sock.bind(("0.0.0.0", 53))
        self._running = True

        while self._running:
            try:
                data, addr = self._sock.recvfrom(256)
                if data and len(data) > 12:
                    response = self._build_response(data)
                    self._sock.sendto(response, addr)
            except OSError:
                pass
            await asyncio.sleep_ms(50)

    def stop(self):
        """Stop the DNS server."""
        self._running = False
        if self._sock:
            self._sock.close()
            self._sock = None
