from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture
def sample_source(tmp_path: Path) -> Path:
    """A small Markdown tree exercising frontmatter, wikilinks, tags, and nesting.

    source/
      index.md            -> title "Home", tags [general], links to [[Second Note]]
      notes/second.md      -> title "Second Note", tags [general, draft]
      notes/third.md        -> no frontmatter, H1 title, links to [[missing note]]
    """
    source = tmp_path / "source"
    (source / "notes").mkdir(parents=True)

    (source / "index.md").write_text(
        "---\n"
        "title: Home\n"
        "tags: [general]\n"
        "---\n"
        "# Home\n\n"
        "Welcome. See [[Second Note]] and [[Second Note|the second note]].\n",
        encoding="utf-8",
    )

    (source / "notes" / "second.md").write_text(
        "---\n"
        "title: Second Note\n"
        "tags: [general, draft]\n"
        "---\n"
        "# Second Note\n\n"
        "Back to [[Home]].\n",
        encoding="utf-8",
    )

    (source / "notes" / "third.md").write_text(
        "# Third\n\n"
        "Links to [[missing note]] which does not exist.\n\n"
        "```\n"
        "[[not a real link]]\n"
        "```\n",
        encoding="utf-8",
    )

    return source
