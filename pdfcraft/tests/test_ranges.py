import pytest

from pdfcraft.ranges import PageRangeError, format_page_ranges, parse_page_ranges


def test_parse_simple_range():
    assert parse_page_ranges("1-3", 10) == [0, 1, 2]


def test_parse_mixed_spec():
    assert parse_page_ranges("1-3, 5, 8-10", 10) == [0, 1, 2, 4, 7, 8, 9]


def test_parse_dedupes_overlap():
    assert parse_page_ranges("1-3,2-4", 10) == [0, 1, 2, 3]


def test_parse_single_page():
    assert parse_page_ranges("5", 10) == [4]


def test_empty_spec_raises():
    with pytest.raises(PageRangeError):
        parse_page_ranges("", 10)


def test_non_numeric_raises():
    with pytest.raises(PageRangeError):
        parse_page_ranges("abc", 10)


def test_out_of_bounds_raises():
    with pytest.raises(PageRangeError):
        parse_page_ranges("1-11", 10)


def test_zero_page_raises():
    with pytest.raises(PageRangeError):
        parse_page_ranges("0", 10)


def test_inverted_range_raises():
    with pytest.raises(PageRangeError):
        parse_page_ranges("5-2", 10)


def test_format_round_trip():
    pages = parse_page_ranges("1-3,5,8-10", 10)
    assert format_page_ranges(pages) == "1-3,5,8-10"


def test_format_empty():
    assert format_page_ranges([]) == ""


def test_format_unsorted_input():
    assert format_page_ranges([4, 0, 1, 2]) == "1-3,5"
