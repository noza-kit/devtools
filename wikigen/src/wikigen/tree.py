from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class TreeNode:
    name: str
    is_folder: bool
    url: str | None = None
    title: str | None = None
    children: list["TreeNode"] = field(default_factory=list)


def build_sidebar_tree(pages) -> list[TreeNode]:
    """Build a nested folder/file tree (folders before files, alphabetical) from pages."""
    root: dict = {}
    for page in pages:
        *dirs, filename = page.rel_path.parts
        node = root
        for d in dirs:
            node = node.setdefault(("dir", d), {})
        node[("file", filename)] = page
    return _to_nodes(root)


def _to_nodes(node: dict) -> list[TreeNode]:
    folders = []
    files = []
    for key, value in node.items():
        kind, name = key
        if kind == "dir":
            folders.append(TreeNode(name=name, is_folder=True, children=_to_nodes(value)))
        else:
            page = value
            files.append(
                TreeNode(name=name, is_folder=False, url=page.output_rel_path, title=page.title)
            )
    folders.sort(key=lambda n: n.name.lower())
    files.sort(key=lambda n: (n.title or "").lower())
    return folders + files
