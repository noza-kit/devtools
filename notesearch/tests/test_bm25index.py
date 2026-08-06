from notesearch.bm25index import BM25Index, tokenize


def test_tokenize_lowercases_and_splits_on_non_word_chars():
    assert tokenize("Docker Build-Error!") == ["docker", "build", "error"]


def test_tokenize_handles_japanese_as_single_run():
    # crude but consistent: a contiguous non-space run of \w chars is one token,
    # so a Japanese word without spaces tokenizes as one unit, not split by character.
    tokens = tokenize("Dockerのビルドエラー")
    assert tokens == ["dockerのビルドエラー"]


def test_search_finds_exact_keyword_match():
    index = BM25Index(["a", "b", "c"], ["apple pie recipe", "banana split", "cherry cake"])
    results = index.search("banana")
    assert results[0].chunk_id == "b"


def test_search_ranks_more_matching_terms_higher():
    # A 2-document corpus where a query term appears in every document
    # gets a negative BM25 IDF for that term (classic Okapi BM25 --
    # "docker" would be treated as unhelpfully common, not distinctive),
    # which BM25Index.search() filters out as score <= 0. A slightly
    # larger corpus avoids that degenerate case and demonstrates the
    # actual ranking behavior instead.
    index = BM25Index(
        ["a", "b", "c", "d"],
        [
            "docker build error solution guide",
            "docker basics introduction",
            "cooking recipes for dinner",
            "gardening tips for spring",
        ],
    )
    results = index.search("docker build error")
    assert results[0].chunk_id == "a"


def test_search_returns_empty_for_no_match():
    index = BM25Index(["a"], ["completely unrelated content"])
    assert index.search("xyzxyzxyz") == []


def test_search_respects_top_k():
    ids = [str(i) for i in range(10)]
    texts = [f"shared keyword document {i}" for i in range(10)]
    index = BM25Index(ids, texts)
    results = index.search("shared keyword", top_k=3)
    assert len(results) <= 3


def test_empty_index_returns_no_results():
    index = BM25Index([], [])
    assert index.search("anything") == []


def test_mismatched_lengths_raises():
    import pytest

    with pytest.raises(ValueError):
        BM25Index(["a", "b"], ["only one text"])
