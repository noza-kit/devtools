from __future__ import annotations

import yaml

_DELIM = "---"


def parse_frontmatter(text: str) -> tuple[dict, str]:
    """Split optional YAML frontmatter from the top of a Markdown file.

    Returns (metadata, body). If the file doesn't start with a `---` line,
    the closing delimiter is missing, or the block isn't valid YAML mapping,
    metadata is empty and body is the original text unchanged.
    """
    if not text.startswith(_DELIM):
        return {}, text

    lines = text.splitlines(keepends=True)
    if not lines or lines[0].strip() != _DELIM:
        return {}, text

    end_index = None
    for i, line in enumerate(lines[1:], start=1):
        if line.strip() == _DELIM:
            end_index = i
            break

    if end_index is None:
        return {}, text

    raw_meta = "".join(lines[1:end_index])
    body = "".join(lines[end_index + 1 :])

    try:
        meta = yaml.safe_load(raw_meta)
    except yaml.YAMLError:
        return {}, text

    if meta is None:
        meta = {}
    elif not isinstance(meta, dict):
        return {}, text

    return meta, body
