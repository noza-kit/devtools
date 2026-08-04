from __future__ import annotations

import ipaddress
import socket

from airshare.network import get_local_ip, is_port_free, is_private_address


def test_is_private_address_accepts_lan_and_loopback() -> None:
    assert is_private_address("192.168.1.10")
    assert is_private_address("10.0.0.5")
    assert is_private_address("127.0.0.1")


def test_is_private_address_rejects_public_and_garbage() -> None:
    assert not is_private_address("8.8.8.8")
    assert not is_private_address("not-an-ip")
    assert not is_private_address("")


def test_get_local_ip_returns_a_valid_ip() -> None:
    ip = get_local_ip()
    ipaddress.ip_address(ip)  # raises ValueError if not a valid address


def test_is_port_free_detects_occupied_port() -> None:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(("127.0.0.1", 0))
    sock.listen(1)
    port = sock.getsockname()[1]
    try:
        assert not is_port_free("127.0.0.1", port)
    finally:
        sock.close()


def test_is_port_free_detects_free_port() -> None:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()

    assert is_port_free("127.0.0.1", port)
