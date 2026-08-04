from __future__ import annotations

import html
import os
import re
from dataclasses import dataclass

# [[Target]] or [[Target|Display text]]; no nested brackets.
_WIKILINK_RE = re.compile(r"\[\[([^\[\]]+)\]\]")
# Segments to leave untouched (fenced/inline code showing the literal syntax).
_PROTECTED_RE = re.compile(r"(<pre[^>]*>.*?</pre>|<code[^>]*>.*?</code>)", re.DOTALL)


@dataclass(frozen=True)
class WikiTarget:
    output_rel_path: str  # posix-style path relative to the site output root


def build_wikilink_index(pages) -> dict[str, WikiTarget]:
    """Map lookup keys (title / filename stem / full path stem, all lowercased) to a page.

    The first page registered for a given key wins, so ambiguous note names
    can be disambiguated in source Markdown with a path, e.g. [[folder/note]].
    """
    index: dict[str, WikiTarget] = {}
    for page in pages:
        target = WikiTarget(output_rel_path=page.output_rel_path)
        for key in _keys_for(page):
            index.setdefault(key, target)
    return index


def _keys_for(page) -> list[str]:
    stem = page.rel_path.stem.lower()
    path_stem = page.rel_path.with_suffix("").as_posix().lower()
    return [page.title.lower(), stem, path_stem]


def resolve_wikilinks(html_text: str, current_output_rel_path: str, index: dict[str, WikiTarget]) -> str:
    """Replace `[[Target]]` / `[[Target|Display]]` markers with anchor tags.

    Text inside <pre>/<code> blocks is left untouched so a fenced code sample
    that shows the wikilink syntax itself isn't converted into a link.
    """
    parts = _PROTECTED_RE.split(html_text)
    # re.split with one capturing group returns the captured (protected) text
    # at odd indices and the surrounding text at even indices.
    return "".join(
        part if i % 2 else _WIKILINK_RE.sub(
            lambda m: _render_link(m, current_output_rel_path, index), part
        )
        for i, part in enumerate(parts)
    )


def _render_link(match: re.Match, current_output_rel_path: str, index: dict[str, WikiTarget]) -> str:
    raw = match.group(1)
    target_name, _, alias = raw.partition("|")
    target_name = html.unescape(target_name).strip()
    display = html.unescape(alias).strip() if alias else target_name

    target = index.get(target_name.lower())
    if target is None:
        title_attr = html.escape(f"Page not found: {target_name}")
        return f'<a class="wikilink wikilink-broken" title="{title_attr}">{html.escape(display)}</a>'

    current_dir = os.path.dirname(current_output_rel_path)
    href = os.path.relpath(target.output_rel_path, start=current_dir or ".")
    href = href.replace(os.sep, "/")
    return f'<a class="wikilink" href="{html.escape(href)}">{html.escape(display)}</a>'
