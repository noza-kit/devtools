from notesearch.hybrid import combine_results, normalize_scores


def test_normalize_scores_min_max():
    result = normalize_scores({"a": 0.0, "b": 5.0, "c": 10.0})
    assert result["a"] == 0.0
    assert result["b"] == 0.5
    assert result["c"] == 1.0


def test_normalize_scores_all_equal_maps_to_one():
    result = normalize_scores({"a": 3.0, "b": 3.0})
    assert result == {"a": 1.0, "b": 1.0}


def test_normalize_scores_empty():
    assert normalize_scores({}) == {}


def test_normalize_scores_single_item():
    assert normalize_scores({"a": 5.0}) == {"a": 1.0}


def test_combine_results_fuses_both_rankings():
    vector_scores = {"a": 0.9, "b": 0.1}
    bm25_scores = {"a": 5.0, "b": 1.0}
    lookup = {
        "a": {"text": "text a", "metadata": {"source": "a.md"}},
        "b": {"text": "text b", "metadata": {"source": "b.md"}},
    }
    results = combine_results(vector_scores, bm25_scores, lookup)
    assert results[0].chunk_id == "a"
    assert results[0].combined_score > results[1].combined_score


def test_combine_results_includes_vector_only_hits():
    vector_scores = {"a": 0.9}
    bm25_scores = {}
    lookup = {"a": {"text": "text a", "metadata": {}}}
    results = combine_results(vector_scores, bm25_scores, lookup)
    assert len(results) == 1
    assert results[0].bm25_score == 0.0


def test_combine_results_includes_bm25_only_hits():
    vector_scores = {}
    bm25_scores = {"b": 3.0}
    lookup = {"b": {"text": "text b", "metadata": {}}}
    results = combine_results(vector_scores, bm25_scores, lookup)
    assert len(results) == 1
    assert results[0].vector_score == 0.0


def test_combine_results_missing_lookup_entry_gets_empty_text():
    results = combine_results({"a": 1.0}, {}, content_lookup={})
    assert results[0].text == ""
    assert results[0].metadata == {}


def test_combine_results_weights_are_configurable():
    vector_scores = {"a": 1.0, "b": 0.0}
    bm25_scores = {"a": 0.0, "b": 1.0}
    lookup = {"a": {"text": "a", "metadata": {}}, "b": {"text": "b", "metadata": {}}}

    vector_favored = combine_results(vector_scores, bm25_scores, lookup, vector_weight=1.0, bm25_weight=0.0)
    assert vector_favored[0].chunk_id == "a"

    bm25_favored = combine_results(vector_scores, bm25_scores, lookup, vector_weight=0.0, bm25_weight=1.0)
    assert bm25_favored[0].chunk_id == "b"


def test_combine_results_sorted_descending():
    vector_scores = {"a": 0.1, "b": 0.9, "c": 0.5}
    lookup = {k: {"text": k, "metadata": {}} for k in vector_scores}
    results = combine_results(vector_scores, {}, lookup)
    scores = [r.combined_score for r in results]
    assert scores == sorted(scores, reverse=True)
