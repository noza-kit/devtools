from __future__ import annotations

import pytest

from tunelab.backends import BackendError, get_backend
from tunelab.backends import optuna_backend, random_backend


def test_get_backend_returns_expected_functions():
    assert get_backend("optuna") is optuna_backend.run
    assert get_backend("random") is random_backend.run_random
    assert get_backend("grid") is random_backend.run_grid


def test_get_backend_unknown_raises():
    with pytest.raises(BackendError):
        get_backend("tensorflow")
