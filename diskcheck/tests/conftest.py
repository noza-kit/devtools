from __future__ import annotations

import pytest


def _write(path, size):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"x" * size)
    return path


@pytest.fixture
def make_file():
    return _write


@pytest.fixture
def sample_tree(tmp_path):
    """A small directory tree with known sizes, for scan/dupes/stale tests.

    tmp_path/
      big.bin       (300 bytes)
      sub/small.bin (50 bytes)
      sub/nested/tiny.bin (10 bytes)
    Total: 360 bytes; sub/ totals 60 bytes.
    """
    _write(tmp_path / "big.bin", 300)
    _write(tmp_path / "sub" / "small.bin", 50)
    _write(tmp_path / "sub" / "nested" / "tiny.bin", 10)
    return tmp_path
