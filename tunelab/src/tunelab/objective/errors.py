from __future__ import annotations


class ObjectiveError(Exception):
    """Raised for objective configuration/setup problems (fatal, stops the run)."""


class TrialFailed(ObjectiveError):
    """Raised when a single trial fails to produce a usable result.

    Callers treat this as a per-trial failure (recorded as a FAILed trial)
    rather than aborting the whole optimization run.
    """

    def __init__(self, message: str, *, returncode: int | None = None, stdout: str = "", stderr: str = ""):
        super().__init__(message)
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr
