from __future__ import annotations

from pathlib import Path
from typing import Optional

from fastapi import Depends, FastAPI, HTTPException, Request, UploadFile, status
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from airshare import files as files_module
from airshare.auth import PASSCODE_HEADER, check_network_access, make_passcode_checker, require_localhost
from airshare.config import Settings
from airshare.network import get_local_ip
from airshare.qr import render_png_data_uri

PACKAGE_DIR = Path(__file__).parent


def create_app(settings: Settings, *, shutdown_token: Optional[str] = None) -> FastAPI:
    """Build the AirShare FastAPI app bound to `settings`.

    `app.state.server` is set by the CLI after construction, to a running
    `uvicorn.Server` instance so the /api/shutdown route can request a
    graceful stop (see cli.py).
    """
    app = FastAPI(title="AirShare", docs_url=None, redoc_url=None)
    app.state.settings = settings
    app.state.shutdown_token = shutdown_token
    app.state.server = None

    templates = Jinja2Templates(directory=str(PACKAGE_DIR / "templates"))
    app.mount("/static", StaticFiles(directory=str(PACKAGE_DIR / "static")), name="static")

    require_passcode = make_passcode_checker(settings)

    @app.get("/", response_class=HTMLResponse)
    def index(request: Request, code: Optional[str] = None) -> HTMLResponse:
        check_network_access(request)
        if settings.passcode:
            supplied = request.headers.get(PASSCODE_HEADER) or code
            if supplied != settings.passcode:
                return templates.TemplateResponse(
                    request, "login.html", {"error": bool(code)}, status_code=status.HTTP_401_UNAUTHORIZED
                )
        return templates.TemplateResponse(request, "index.html", {"code": code or ""})

    @app.get("/qr", response_class=HTMLResponse)
    def qr_page(request: Request, _auth: None = Depends(require_localhost)) -> HTMLResponse:
        ip = get_local_ip()
        url = f"http://{ip}:{settings.port}/"
        if settings.passcode:
            url = f"{url}?code={settings.passcode}"
        return templates.TemplateResponse(
            request,
            "qr.html",
            {"url": url, "qr_data_uri": render_png_data_uri(url), "passcode": settings.passcode},
        )

    @app.get("/api/files")
    def api_list_files(_auth: None = Depends(require_passcode)) -> list[dict]:
        return [entry.__dict__ for entry in files_module.list_files(settings.send_dir)]

    @app.get("/api/files/{name}")
    def api_download_file(name: str, _auth: None = Depends(require_passcode)) -> FileResponse:
        try:
            path = files_module.resolve_download_path(settings.send_dir, name)
        except ValueError as exc:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
        except FileNotFoundError as exc:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "File not found") from exc
        return FileResponse(path, filename=path.name)

    @app.post("/api/upload")
    async def api_upload(file: UploadFile, _auth: None = Depends(require_passcode)) -> JSONResponse:
        content = await file.read()
        if not content:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Empty file")
        try:
            saved = files_module.save_upload(settings.receive_dir, file.filename or "upload", content)
        except ValueError as exc:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
        return JSONResponse({"saved_as": saved.name})

    @app.get("/api/health")
    def health() -> dict:
        return {"status": "ok"}

    @app.post("/api/shutdown")
    async def shutdown(request: Request, _auth: None = Depends(require_localhost)) -> dict:
        token = request.headers.get("X-AirShare-Token")
        if not shutdown_token or token != shutdown_token:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Invalid shutdown token")
        server = app.state.server
        if server is not None:
            server.should_exit = True
        return {"status": "stopping"}

    return app
