from __future__ import annotations

import html as _html

import jinja2

from wikigen.tree import TreeNode

_env = jinja2.Environment(
    loader=jinja2.PackageLoader("wikigen", "templates"),
    autoescape=True,
    trim_blocks=True,
    lstrip_blocks=True,
)


def root_prefix_for(output_rel_path: str) -> str:
    """"../" repeated once per directory level, so assets/links resolve from any depth."""
    depth = output_rel_path.count("/")
    return "../" * depth


def render_tree_html(nodes: list[TreeNode], root_prefix: str, current_url: str | None) -> str:
    if not nodes:
        return ""
    items = []
    for node in nodes:
        if node.is_folder:
            items.append(
                f"<li class=\"wikigen-tree-folder\"><span>{_html.escape(node.name)}</span>"
                f"{render_tree_html(node.children, root_prefix, current_url)}</li>"
            )
        else:
            href = root_prefix + node.url
            css = "wikigen-tree-file"
            if node.url == current_url:
                css += " active"
            items.append(
                f'<li class="{css}"><a href="{_html.escape(href)}">'
                f"{_html.escape(node.title)}</a></li>"
            )
    return "<ul>" + "".join(items) + "</ul>"


def _base_context(tree, root_prefix, current_url, site_title) -> dict:
    return {
        "site_title": site_title,
        "root_prefix": root_prefix,
        "tree_html": render_tree_html(tree, root_prefix, current_url),
    }


def render_page_html(page, tree, tag_slug_by_name, site_title) -> str:
    root_prefix = root_prefix_for(page.output_rel_path)
    ctx = _base_context(tree, root_prefix, page.output_rel_path, site_title)
    ctx.update(
        title=page.title,
        page_title=page.title,
        body_html=page.html,
        tags=[{"name": t, "slug": tag_slug_by_name.get(t, "")} for t in page.tags],
    )
    return _env.get_template("page.html").render(**ctx)


def render_tag_index_html(tag_index, slug_by_name, tree, site_title) -> str:
    root_prefix = "../"
    ctx = _base_context(tree, root_prefix, None, site_title)
    tags = [
        {"name": name, "slug": slug_by_name[name], "count": len(pages)}
        for name, pages in sorted(tag_index.items(), key=lambda kv: kv[0].lower())
    ]
    ctx.update(title="Tags", tags=tags)
    return _env.get_template("tag_index.html").render(**ctx)


def render_tag_page_html(tag_name, pages, tree, site_title) -> str:
    root_prefix = "../"
    ctx = _base_context(tree, root_prefix, None, site_title)
    ctx.update(
        title=f"#{tag_name}",
        tag_name=tag_name,
        pages=[{"title": p.title, "url": p.output_rel_path} for p in pages],
    )
    return _env.get_template("tag_page.html").render(**ctx)


def render_fallback_index_html(pages, tree, site_title) -> str:
    root_prefix = ""
    ctx = _base_context(tree, root_prefix, "index.html", site_title)
    items = "".join(
        f'<li><a href="{_html.escape(p.output_rel_path)}">{_html.escape(p.title)}</a></li>'
        for p in sorted(pages, key=lambda p: p.title.lower())
    )
    ctx.update(
        title=site_title,
        page_title=site_title,
        body_html=f'<ul class="wikigen-page-list">{items}</ul>',
        tags=[],
    )
    return _env.get_template("page.html").render(**ctx)
