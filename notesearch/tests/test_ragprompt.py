from notesearch.hybrid import SearchResult
from notesearch.ragprompt import QUESTION_PLACEHOLDER, format_rag_prompt


def _result(text: str, source: str) -> SearchResult:
    return SearchResult(chunk_id="x", text=text, metadata={"source": source})


def test_format_rag_prompt_structure():
    results = [_result("chunk one text", "a.md"), _result("chunk two text", "b.md")]
    prompt = format_rag_prompt(results)
    assert prompt.startswith("以下の参考資料を基に、私の質問に回答してください。")
    assert "[資料1: a.md]" in prompt
    assert "chunk one text" in prompt
    assert "[資料2: b.md]" in prompt
    assert "chunk two text" in prompt
    assert prompt.rstrip().endswith(f"質問：{QUESTION_PLACEHOLDER}")


def test_format_rag_prompt_with_real_question():
    results = [_result("chunk text", "a.md")]
    prompt = format_rag_prompt(results, question="実際の質問です")
    assert "質問：実際の質問です" in prompt
    assert QUESTION_PLACEHOLDER not in prompt


def test_format_rag_prompt_empty_results():
    prompt = format_rag_prompt([])
    assert "以下の参考資料を基に" in prompt
    assert f"質問：{QUESTION_PLACEHOLDER}" in prompt


def test_format_rag_prompt_missing_source_metadata():
    result = SearchResult(chunk_id="x", text="text", metadata={})
    prompt = format_rag_prompt([result])
    assert "[資料1: unknown]" in prompt
