from __future__ import annotations

from devtoolbox.common.paths import experiments_db_path
from devtoolbox.explog.db import get_connection, insert_run


def log_run(params: dict, results: dict, tags: list[str] = None) -> int:
    """Record one experiment run to ~/.devtools/experiments.db.

    Generic by design: any script (ML training, benchmarks, data pipelines,
    ...) can call this with whatever params/results dicts make sense for it.
    Values that aren't natively JSON-serializable (e.g. numpy scalars) are
    stored via str() rather than raising.

    Returns the new run's id.
    """
    conn = get_connection(experiments_db_path())
    try:
        return insert_run(conn, params, results, tags or [])
    finally:
        conn.close()
