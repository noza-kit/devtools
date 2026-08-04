from __future__ import annotations

import gc

import optuna

from tunelab.config import Config
from tunelab.paths import storage_url, study_db_path


class StudyNotFoundError(Exception):
    pass


def open_study(config: Config, fresh: bool = False) -> optuna.Study:
    """Create (or resume) the study backing a config's `run`."""
    url = storage_url(config.study)
    if fresh:
        try:
            optuna.delete_study(study_name=config.study, storage=url)
        except KeyError:
            pass
    return optuna.create_study(
        study_name=config.study,
        storage=url,
        direction=config.direction,
        load_if_exists=True,
    )


def load_study(study_name: str) -> optuna.Study:
    if not study_db_path(study_name).exists():
        raise StudyNotFoundError(f"No study named {study_name!r} found")
    return optuna.load_study(study_name=study_name, storage=storage_url(study_name))


def delete_study(study_name: str) -> None:
    if not study_db_path(study_name).exists():
        raise StudyNotFoundError(f"No study named {study_name!r} found")
    optuna.delete_study(study_name=study_name, storage=storage_url(study_name))
    # Any Study/RDBStorage objects from earlier calls (e.g. open_study) may still hold an
    # open sqlite file handle until garbage collected; force collection so the unlink below
    # doesn't hit a PermissionError on Windows.
    gc.collect()
    study_db_path(study_name).unlink(missing_ok=True)
