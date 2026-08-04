from __future__ import annotations

import dataclasses

import pytest
from starlette.testclient import TestClient

from airshare.config import Settings
from airshare.server import create_app

LAN_CLIENT = ("192.168.1.50", 12345)
PUBLIC_CLIENT = ("8.8.8.8", 12345)
LOCALHOST_CLIENT = ("127.0.0.1", 12345)


def make_client(settings: Settings, *, client=LAN_CLIENT, shutdown_token: str | None = None) -> TestClient:
    app = create_app(settings, shutdown_token=shutdown_token)
    return TestClient(app, client=client)


def test_index_ok_without_passcode(settings: Settings) -> None:
    client = make_client(settings)
    response = client.get("/")
    assert response.status_code == 200
    assert "AirShare" in response.text


def test_index_rejects_non_lan_client(settings: Settings) -> None:
    client = make_client(settings, client=PUBLIC_CLIENT)
    response = client.get("/")
    assert response.status_code == 403


def test_index_requires_passcode_when_set(settings: Settings) -> None:
    protected = dataclasses.replace(settings, passcode="1234")
    client = make_client(protected)

    no_code = client.get("/")
    assert no_code.status_code == 401

    wrong_code = client.get("/", params={"code": "0000"})
    assert wrong_code.status_code == 401

    right_code = client.get("/", params={"code": "1234"})
    assert right_code.status_code == 200


def test_api_files_lists_send_dir(settings: Settings) -> None:
    (settings.send_dir / "report.pdf").write_bytes(b"%PDF-1.4")
    client = make_client(settings)

    response = client.get("/api/files")
    assert response.status_code == 200
    names = [entry["name"] for entry in response.json()]
    assert names == ["report.pdf"]


def test_api_download_file(settings: Settings) -> None:
    (settings.send_dir / "photo.jpg").write_bytes(b"jpegdata")
    client = make_client(settings)

    response = client.get("/api/files/photo.jpg")
    assert response.status_code == 200
    assert response.content == b"jpegdata"


def test_api_download_missing_file_is_404(settings: Settings) -> None:
    client = make_client(settings)
    response = client.get("/api/files/missing.jpg")
    assert response.status_code == 404


def test_api_upload_saves_to_receive_dir(settings: Settings) -> None:
    client = make_client(settings)
    response = client.post("/api/upload", files={"file": ("note.txt", b"hello", "text/plain")})

    assert response.status_code == 200
    assert response.json() == {"saved_as": "note.txt"}
    assert (settings.receive_dir / "note.txt").read_bytes() == b"hello"


def test_api_requires_passcode(settings: Settings) -> None:
    protected = dataclasses.replace(settings, passcode="1234")
    client = make_client(protected)

    denied = client.get("/api/files")
    assert denied.status_code == 401

    allowed = client.get("/api/files", headers={"X-AirShare-Code": "1234"})
    assert allowed.status_code == 200


def test_qr_page_allows_localhost_only(settings: Settings) -> None:
    localhost_client = make_client(settings, client=LOCALHOST_CLIENT)
    lan_client = make_client(settings, client=LAN_CLIENT)

    ok = localhost_client.get("/qr")
    assert ok.status_code == 200

    denied = lan_client.get("/qr")
    assert denied.status_code == 403


def test_shutdown_requires_valid_token(settings: Settings) -> None:
    client = make_client(settings, client=LOCALHOST_CLIENT, shutdown_token="secret-token")

    no_token = client.post("/api/shutdown")
    assert no_token.status_code == 403

    wrong_token = client.post("/api/shutdown", headers={"X-AirShare-Token": "nope"})
    assert wrong_token.status_code == 403

    right_token = client.post("/api/shutdown", headers={"X-AirShare-Token": "secret-token"})
    assert right_token.status_code == 200


def test_shutdown_rejects_non_localhost(settings: Settings) -> None:
    client = make_client(settings, client=LAN_CLIENT, shutdown_token="secret-token")
    response = client.post("/api/shutdown", headers={"X-AirShare-Token": "secret-token"})
    assert response.status_code == 403


def test_health_check(settings: Settings) -> None:
    client = make_client(settings)
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
