from __future__ import annotations

import ipaddress

from airshare.network import get_local_ip, is_private_address


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
