from __future__ import annotations

import ipaddress
import socket


def get_local_ip() -> str:
    """Best-effort detection of this machine's LAN IP address.

    Opens a UDP socket toward a public address without sending any packet,
    just to let the OS pick the outbound interface's address.
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.connect(("8.8.8.8", 80))
        return sock.getsockname()[0]
    except OSError:
        try:
            return socket.gethostbyname(socket.gethostname())
        except OSError:
            return "127.0.0.1"
    finally:
        sock.close()


def is_private_address(host: str) -> bool:
    """Whether `host` is a loopback or RFC1918 LAN address."""
    try:
        addr = ipaddress.ip_address(host)
    except ValueError:
        return False
    return addr.is_loopback or addr.is_private
