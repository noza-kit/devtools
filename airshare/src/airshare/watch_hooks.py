from __future__ import annotations

import logging
import subprocess
from pathlib import Path
from typing import Optional

logger = logging.getLogger("airshare.watch")

HOOK_TIMEOUT_SECONDS = 300


def run_hook(command_template: str, filepath: Path) -> bool:
    """Runs a configured hook command for one routed file via the shell
    (`shell=True`) rather than splitting into argv ourselves -- avoids
    re-deriving the same shlex-vs-Windows-backslash-path problem this
    session already hit elsewhere (pdfcraft/notesearch), and lets a
    hook template use ordinary shell syntax. Never raises: a failing or
    crashing hook must not block routing/notification for this or any
    other file in the batch."""
    command = command_template.format(filepath=str(filepath))
    try:
        result = subprocess.run(
            command, shell=True, capture_output=True, text=True, timeout=HOOK_TIMEOUT_SECONDS
        )
        if result.returncode != 0:
            logger.warning("hook failed (%s): %s", command, result.stderr.strip())
        return result.returncode == 0
    except Exception:
        logger.exception("hook execution error: %s", command)
        return False


def run_hooks_for_file(hooks: dict[str, str], filepath: Path) -> Optional[bool]:
    """Runs whichever hook matches `filepath`'s extension. Returns None
    if no hook is configured for that extension (nothing to run), else
    the hook's success/failure."""
    template = hooks.get(filepath.suffix.lower())
    if not template:
        return None
    return run_hook(template, filepath)
