from __future__ import annotations

from typing import Callable, Optional

from fastapi import HTTPException, Query, Request, status

from airshare.config import Settings
from airshare.network import is_private_address

PASSCODE_HEADER = "X-AirShare-Code"
LOCALHOST_ADDRESSES = {"127.0.0.1", "::1"}


def check_network_access(request: Request) -> None:
    """Reject any request whose client address is not on a private/loopback network."""
    client_host = request.client.host if request.client else None
    if not client_host or not is_private_address(client_host):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Access is restricted to the local network")


def require_localhost(request: Request) -> None:
    """Reject anything that didn't originate from this machine (used for /qr and shutdown)."""
    client_host = request.client.host if request.client else None
    if client_host not in LOCALHOST_ADDRESSES:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "This endpoint is only available on localhost")


def make_passcode_checker(settings: Settings) -> Callable[..., None]:
    """Build a FastAPI dependency that enforces the LAN-only + passcode policy for `settings`."""

    def check_passcode(request: Request, code: Optional[str] = Query(default=None)) -> None:
        check_network_access(request)
        if not settings.passcode:
            return
        supplied = request.headers.get(PASSCODE_HEADER) or code
        if supplied != settings.passcode:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or missing passcode")

    return check_passcode
