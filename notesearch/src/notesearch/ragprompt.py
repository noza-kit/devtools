from __future__ import annotations

from notesearch.hybrid import SearchResult

QUESTION_PLACEHOLDER = "[ここにプロンプトを入力]"


def format_rag_prompt(results: list[SearchResult], question: str = QUESTION_PLACEHOLDER) -> str:
    """The spec's exact RAG prompt template: numbered [資料N: source]
    blocks, each followed by that chunk's text, then the question at
    the end (either a real question for --ask, or the placeholder for
    --copy)."""
    lines = ["以下の参考資料を基に、私の質問に回答してください。"]
    for i, result in enumerate(results, start=1):
        source = result.metadata.get("source", "unknown")
        lines.append("---")
        lines.append(f"[資料{i}: {source}]")
        lines.append(result.text)
    lines.append("---")
    lines.append(f"質問：{question}")
    return "\n".join(lines)


def copy_to_clipboard(text: str) -> None:
    import pyperclip

    pyperclip.copy(text)
