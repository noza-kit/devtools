from __future__ import annotations

import os
import stat
from pathlib import Path
from typing import Optional

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

# Read-only: mailwatch only reads messages/attachments, it never modifies or
# deletes anything in the mailbox.
SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]


class AuthError(Exception):
    pass


def _write_token(token_path: Path, creds: Credentials) -> None:
    token_path.parent.mkdir(parents=True, exist_ok=True)
    token_path.write_text(creds.to_json(), encoding="utf-8")
    if os.name != "nt":
        token_path.chmod(stat.S_IRUSR | stat.S_IWUSR)


def load_credentials(credentials_path: Path, token_path: Path, *, interactive: bool = True) -> Credentials:
    """Return valid Gmail API credentials.

    Reads `token_path` if present. An expired token is refreshed silently via
    its refresh_token. If there is no usable token, this runs the OAuth2
    consent flow (opens a browser) using `credentials_path` — the OAuth
    client secrets JSON downloaded from Google Cloud Console (OAuth client
    ID, type "Desktop app") — and writes the resulting token to `token_path`.

    With `interactive=False`, never opens a browser: raises AuthError instead
    of falling back to the consent flow, for use in the unattended polling
    loop where a stuck browser prompt would just hang.
    """
    creds: Optional[Credentials] = None
    if token_path.exists():
        creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)

    if creds and creds.valid:
        return creds

    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
            _write_token(token_path, creds)
            return creds
        except Exception as exc:
            if not interactive:
                raise AuthError(
                    f"Failed to refresh Gmail token: {exc}. Run `mailwatch auth --force` again."
                ) from exc
            creds = None

    if not interactive:
        raise AuthError(f"No valid Gmail token at {token_path}. Run `mailwatch auth` first.")

    if not credentials_path.exists():
        raise AuthError(
            f"OAuth client credentials not found at {credentials_path}. "
            "Create an OAuth client ID (type 'Desktop app') in Google Cloud Console, "
            "download its JSON, and save it there (or pass --credentials)."
        )

    flow = InstalledAppFlow.from_client_secrets_file(str(credentials_path), SCOPES)
    creds = flow.run_local_server(port=0)
    _write_token(token_path, creds)
    return creds


def refresh_if_needed(creds: Credentials, token_path: Path) -> Credentials:
    """Refresh `creds` in place if expired, persisting the new token. Raises
    AuthError (rather than opening a browser) if the refresh fails."""
    if not creds.expired:
        return creds
    try:
        creds.refresh(Request())
        _write_token(token_path, creds)
    except Exception as exc:
        raise AuthError(f"Failed to refresh Gmail token: {exc}. Run `mailwatch auth --force` again.") from exc
    return creds
