from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional

from rich.console import Console
from rich.tree import Tree

from diskcheck.fsutils import human_size


@dataclass
class ScanNode:
    """One file or directory in a scanned tree, with aggregated size."""

    path: Path
    size: int = 0
    is_dir: bool = False
    error: Optional[str] = None
    children: list["ScanNode"] = field(default_factory=list)

    def top_children(self, top: Optional[int] = None) -> list["ScanNode"]:
        ranked = sorted(self.children, key=lambda c: c.size, reverse=True)
        return ranked[:top] if top is not None else ranked

    def to_dict(self, top: Optional[int] = None, max_depth: Optional[int] = None, _depth: int = 0) -> dict:
        data: dict = {
            "path": str(self.path),
            "name": self.path.name or str(self.path),
            "size": self.size,
            "size_human": human_size(self.size),
            "is_dir": self.is_dir,
        }
        if self.error:
            data["error"] = self.error
        if self.is_dir:
            if max_depth is not None and _depth >= max_depth:
                data["children"] = []
            else:
                data["children"] = [
                    c.to_dict(top=top, max_depth=max_depth, _depth=_depth + 1) for c in self.top_children(top)
                ]
        return data


def scan_tree(root: Path, *, on_entry: Optional[Callable[[ScanNode], None]] = None) -> ScanNode:
    """Recursively scan `root`, aggregating directory sizes bottom-up.

    Entries that can't be read (permission errors, broken symlinks, ...) are
    kept in the tree with an `error` message instead of aborting the scan.
    Symlinked directories are recorded as their own (small) entry rather than
    followed, to avoid double-counting and symlink loops.
    """
    root = Path(root)

    if not root.is_dir():
        try:
            size = root.stat().st_size
        except OSError as exc:
            node = ScanNode(path=root, error=str(exc))
        else:
            node = ScanNode(path=root, size=size)
        if on_entry:
            on_entry(node)
        return node

    node = ScanNode(path=root, is_dir=True)
    try:
        entries = list(os.scandir(root))
    except OSError as exc:
        node.error = str(exc)
        if on_entry:
            on_entry(node)
        return node

    for entry in entries:
        try:
            is_dir = entry.is_dir(follow_symlinks=False)
        except OSError as exc:
            child = ScanNode(path=Path(entry.path), error=str(exc))
            node.children.append(child)
            if on_entry:
                on_entry(child)
            continue

        if is_dir:
            child = scan_tree(Path(entry.path), on_entry=on_entry)
        else:
            try:
                stat = entry.stat(follow_symlinks=False)
                child = ScanNode(path=Path(entry.path), size=stat.st_size)
            except OSError as exc:
                child = ScanNode(path=Path(entry.path), error=str(exc))
            if on_entry:
                on_entry(child)

        node.children.append(child)
        node.size += child.size

    return node


def render_tree(node: ScanNode, *, top: int = 20, max_depth: int = 2) -> Tree:
    """Build a `rich.tree.Tree` showing, at each level down to `max_depth`,
    the top-N largest children by size."""

    def build(n: ScanNode, depth: int) -> Tree:
        label = f"[bold cyan]{human_size(n.size):>10}[/bold cyan]  {n.path.name or str(n.path)}"
        if n.error:
            label += f"  [red](error: {n.error})[/red]"
        branch = Tree(label)
        if not n.is_dir:
            return branch
        if depth >= max_depth:
            if n.children:
                branch.add(f"[dim]... {len(n.children)} item(s), use --depth to expand[/dim]")
            return branch
        shown = n.top_children(top)
        for child in shown:
            branch.add(build(child, depth + 1))
        remaining = len(n.children) - len(shown)
        if remaining > 0:
            branch.add(f"[dim]... {remaining} more item(s) not shown (use --top to expand)[/dim]")
        return branch

    return build(node, 0)


def interactive_browse(root: ScanNode, *, top: int = 20, console: Optional[Console] = None) -> None:
    """Text-based drill-down browser: pick a numbered child to descend into,
    `u` to go back up, `q` to quit."""
    console = console or Console()
    stack = [root]

    while True:
        current = stack[-1]
        console.print(f"\n[bold]{current.path}[/bold]  total: [bold cyan]{human_size(current.size)}[/bold cyan]")
        children = current.top_children(top)
        for i, child in enumerate(children, start=1):
            marker = "/" if child.is_dir else ""
            console.print(f"  [{i:>2}] {human_size(child.size):>10}  {child.path.name}{marker}")
        if not children:
            console.print("  (empty)")

        console.print("  \\[u] up   \\[q] quit")
        choice = console.input("> ").strip().lower()

        if choice == "q":
            return
        if choice == "u":
            if len(stack) > 1:
                stack.pop()
            continue
        if choice.isdigit():
            idx = int(choice) - 1
            if 0 <= idx < len(children) and children[idx].is_dir:
                stack.append(children[idx])
