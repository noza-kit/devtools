from datetime import datetime
from pathlib import Path

import pytest

from batchimg.naming import RenameTemplateError, render_filename

MTIME = datetime(2026, 3, 5, 12, 0, 0)


def test_no_template_keeps_original_name():
    name = render_filename(Path("photo.jpg"), 1, None, mtime=MTIME)
    assert name == "photo.jpg"


def test_sequence_placeholder_is_zero_padded():
    name = render_filename(Path("photo.jpg"), 7, "img_{n}", mtime=MTIME, digits=4)
    assert name == "img_0007.jpg"


def test_sequence_placeholder_not_truncated_beyond_digits():
    name = render_filename(Path("photo.jpg"), 12345, "img_{n}", mtime=MTIME, digits=4)
    assert name == "img_12345.jpg"


def test_date_placeholder_uses_date_format():
    name = render_filename(Path("photo.jpg"), 1, "{date}_{n}", mtime=MTIME, date_format="%Y-%m-%d")
    assert name == "2026-03-05_0001.jpg"


def test_stem_and_ext_placeholders():
    name = render_filename(Path("holiday.PNG"), 1, "{stem}_{ext}", mtime=MTIME)
    assert name == "holiday_png.png"


def test_template_with_explicit_extension_is_kept_as_is():
    name = render_filename(Path("holiday.png"), 1, "converted_{n}.jpg", mtime=MTIME)
    assert name == "converted_0001.jpg"


def test_unknown_placeholder_raises():
    with pytest.raises(RenameTemplateError):
        render_filename(Path("photo.jpg"), 1, "{bogus}", mtime=MTIME)
