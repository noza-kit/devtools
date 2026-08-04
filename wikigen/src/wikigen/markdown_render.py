from __future__ import annotations

import markdown as _markdown

_EXTENSIONS = ["extra", "toc", "sane_lists"]


def render_markdown(body: str) -> str:
    """Render a Markdown body (frontmatter already stripped) to an HTML fragment."""
    return _markdown.markdown(body, extensions=_EXTENSIONS, output_format="html5")
