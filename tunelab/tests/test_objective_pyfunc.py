from __future__ import annotations

import pytest

from tunelab.config import ObjectiveSpec
from tunelab.objective.errors import ObjectiveError
from tunelab.objective.pyfunc import load_entrypoint, run_pyfunc_objective


def test_run_pyfunc_objective_calls_function(quadratic_module):
    spec = ObjectiveSpec(mode="callable", entrypoint=f"{quadratic_module}:objective")
    value = run_pyfunc_objective(spec, {"x": 5.0})
    assert value == pytest.approx(4.0)


def test_entrypoint_without_colon_raises():
    with pytest.raises(ObjectiveError):
        load_entrypoint("no_colon_here")


def test_unimportable_module_raises():
    with pytest.raises(ObjectiveError):
        load_entrypoint("definitely.not.a.real.module:func")


def test_missing_attribute_raises(quadratic_module):
    with pytest.raises(ObjectiveError):
        load_entrypoint(f"{quadratic_module}:does_not_exist")


def test_propagates_user_exceptions(quadratic_module):
    spec = ObjectiveSpec(mode="callable", entrypoint=f"{quadratic_module}:always_fails")
    with pytest.raises(ValueError):
        run_pyfunc_objective(spec, {"x": 1.0})
