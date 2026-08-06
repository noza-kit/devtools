import pytest

from notesearch.chunking import Chunk, chunk_text, fixed_size_chunks, split_by_headings


def test_split_by_headings_basic():
    text = "# Title\nBody line 1\nBody line 2\n\n## Sub\nSub body\n"
    sections = split_by_headings(text)
    assert sections[0] == ("Title", "Body line 1\nBody line 2", 2)
    assert sections[1] == ("Sub", "Sub body", 6)  # "## Sub" is line 5, its body starts line 6


def test_split_by_headings_no_headings_at_all_is_still_one_section():
    # No "# heading" anywhere -> the whole text is captured as a single
    # heading="" section (not []) -- chunk_text's own no-headings
    # fallback only ever triggers for genuinely empty/whitespace input.
    text = "Just plain text\nwith two lines"
    assert split_by_headings(text) == [("", text, 1)]


def test_split_by_headings_content_before_first_heading():
    text = "Intro text\n# First Heading\nBody"
    sections = split_by_headings(text)
    assert sections[0] == ("", "Intro text", 1)
    assert sections[1] == ("First Heading", "Body", 3)


def test_split_by_headings_drops_empty_sections():
    text = "# A\n# B\nBody of B"
    sections = split_by_headings(text)
    assert len(sections) == 1
    assert sections[0][0] == "B"


def test_split_by_headings_recognizes_h1_through_h6():
    text = "###### Deep heading\nbody"
    sections = split_by_headings(text)
    assert sections[0][0] == "Deep heading"


def test_fixed_size_chunks_short_text_returns_single_chunk():
    result = fixed_size_chunks("short text", start_line=5, size=500)
    assert result == [("short text", 5)]


def test_fixed_size_chunks_splits_long_text_with_overlap():
    text = "a" * 1000
    result = fixed_size_chunks(text, start_line=1, size=400, overlap=50)
    pieces = [p for p, _ in result]
    assert len(pieces) == 3
    assert pieces[0] == "a" * 400
    # consecutive pieces overlap by exactly `overlap` characters
    assert pieces[0][-50:] == pieces[1][:50]


def test_fixed_size_chunks_overlap_must_be_smaller_than_size():
    with pytest.raises(ValueError):
        fixed_size_chunks("x" * 100, size=50, overlap=50)


def test_fixed_size_chunks_line_numbers_advance_with_newlines():
    text = "\n".join(f"line{i}" for i in range(200))  # long text with many newlines
    result = fixed_size_chunks(text, start_line=1, size=300, overlap=20)
    lines = [line for _, line in result]
    assert lines == sorted(lines)  # line numbers should only increase
    assert lines[0] == 1
    assert lines[-1] > 1


def test_chunk_text_short_document_with_headings():
    text = "# Heading\nShort body"
    chunks = chunk_text(text)
    assert chunks == [Chunk(text="Short body", heading="Heading", start_line=2)]


def test_chunk_text_no_headings_falls_back_to_whole_document():
    text = "Just some plain text, no headings anywhere."
    chunks = chunk_text(text)
    assert len(chunks) == 1
    assert chunks[0].heading == ""
    assert chunks[0].text == text


def test_chunk_text_empty_document_produces_no_chunks():
    assert chunk_text("") == []
    assert chunk_text("   \n  \n") == []


def test_chunk_text_heading_with_no_body_falls_back_to_raw_text():
    # split_by_headings drops a heading with nothing under it (empty
    # section body), so chunk_text's own fallback picks up the raw
    # (stripped) text instead of silently producing zero chunks.
    chunks = chunk_text("# Empty Heading")
    assert len(chunks) == 1
    assert chunks[0].text == "# Empty Heading"
    assert chunks[0].heading == ""


def test_chunk_text_long_section_gets_further_split():
    text = "# Heading\n" + "word " * 300  # long body under one heading
    chunks = chunk_text(text, size=200, overlap=20)
    assert len(chunks) > 1
    assert all(c.heading == "Heading" for c in chunks)


def test_chunk_text_multiple_headings_each_own_chunks():
    text = "# A\nBody A\n# B\nBody B\n# C\nBody C"
    chunks = chunk_text(text)
    assert [c.heading for c in chunks] == ["A", "B", "C"]
    assert [c.text for c in chunks] == ["Body A", "Body B", "Body C"]
