from __future__ import annotations

from pathlib import Path
from typing import Optional

from PIL import Image
from pptx import Presentation
from pptx.enum.shapes import PP_PLACEHOLDER_TYPE as PPT
from pptx.presentation import Presentation as PresentationType
from pptx.shapes.picture import Picture
from pptx.slide import Slide

from slidecraft.parser import ContentItem, ImageRef, SlideData

_LAYOUT_PREFERENCE_WITH_IMAGE = ("Two Content", "Comparison", "Content with Caption", "Picture with Caption")
_LAYOUT_PREFERENCE_TEXT_ONLY = ("Title and Content", "Section Header", "Title Slide")
_TEXT_PLACEHOLDER_TYPES = {PPT.BODY, PPT.OBJECT, PPT.SUBTITLE}
_IMAGE_PLACEHOLDER_TYPES = {PPT.OBJECT, PPT.PICTURE, PPT.BODY}


def build_presentation(slides: list[SlideData], template_path: Optional[Path] = None) -> PresentationType:
    """Build a PPTX from parsed slide data. `template_path` is a
    "master" .pptx whose fonts/background/placeholder positions are
    reused as the base for every generated slide, exactly like starting
    a new presentation from that file in PowerPoint. With no
    `template_path`, this uses python-pptx's own bundled default
    template (a plain white background, standard fonts) — satisfying
    the "works with no --template" requirement without shipping a
    redundant duplicate default .pptx of our own."""
    prs = Presentation(str(template_path)) if template_path else Presentation()
    for slide_data in slides:
        _add_slide(prs, slide_data)
    return prs


def _add_slide(prs: PresentationType, data: SlideData) -> Slide:
    layout = _pick_layout(prs, has_image=bool(data.images))
    slide = prs.slides.add_slide(layout)

    if slide.shapes.title is not None:
        slide.shapes.title.text = data.title

    body_ph = _find_text_placeholder(slide)
    if body_ph is not None and data.content_items:
        _fill_text(body_ph.text_frame, data.content_items)

    if data.images:
        # `slide.placeholders` hands back a fresh wrapper object on every
        # access (even for the same underlying element), so excluding
        # body_ph by `is` identity silently never matches -- compare by
        # idx instead.
        exclude_idx = body_ph.placeholder_format.idx if body_ph is not None else None
        _place_images(prs, slide, data.images, exclude_idx=exclude_idx)

    if data.notes:
        slide.notes_slide.notes_text_frame.text = data.notes

    return slide


def _pick_layout(prs: PresentationType, has_image: bool):
    """Best-effort layout auto-selection by conventional PowerPoint
    layout name (see README's "Known limitations" for why this is
    heuristic, not guaranteed, on an arbitrary custom template)."""
    by_name = {layout.name: layout for layout in prs.slide_layouts}
    preferred = _LAYOUT_PREFERENCE_WITH_IMAGE if has_image else _LAYOUT_PREFERENCE_TEXT_ONLY

    for name in preferred:
        if name in by_name:
            return by_name[name]

    # Fallback: any layout with a title placeholder plus at least one
    # other (body/content) placeholder.
    for layout in prs.slide_layouts:
        non_title = [p for p in layout.placeholders if p.placeholder_format.idx != 0]
        if non_title:
            return layout

    return prs.slide_layouts[0]


def _find_text_placeholder(slide: Slide):
    for ph in slide.placeholders:
        if ph.placeholder_format.idx == 0:  # title
            continue
        if ph.placeholder_format.type in _TEXT_PLACEHOLDER_TYPES:
            return ph
    return None


def _fill_text(text_frame, items: list[ContentItem]) -> None:
    text_frame.clear()
    for i, item in enumerate(items):
        paragraph = text_frame.paragraphs[0] if i == 0 else text_frame.add_paragraph()
        paragraph.level = item.level if item.kind == "bullet" else 0
        for run in item.runs:
            r = paragraph.add_run()
            r.text = run.text
            r.font.bold = run.bold
            r.font.italic = run.italic


def _place_images(prs: PresentationType, slide: Slide, images: list[ImageRef], exclude_idx: Optional[int] = None) -> None:
    image_ph = None
    for ph in slide.placeholders:
        if ph.placeholder_format.idx in (0, exclude_idx):
            continue
        if ph.placeholder_format.type in _IMAGE_PLACEHOLDER_TYPES:
            image_ph = ph
            break

    if image_ph is not None:
        left, top, width, height = image_ph.left, image_ph.top, image_ph.width, image_ph.height
        image_ph._element.getparent().remove(image_ph._element)
    else:
        # No spare placeholder (e.g. a text-only custom layout got picked
        # anyway): fall back to a fixed region in the slide's right half.
        left = int(prs.slide_width * 0.55)
        top = int(prs.slide_height * 0.2)
        width = int(prs.slide_width * 0.4)
        height = int(prs.slide_height * 0.65)

    first, *rest = images
    _insert_image_fit(slide, first.path, left, top, width, height)

    # Additional images on the same slide stack below the first, each
    # given an equal share of the remaining vertical space.
    if rest:
        stack_height = height // (len(rest) + 1)
        y = top + stack_height
        for img in rest:
            _insert_image_fit(slide, img.path, left, y, width, stack_height)
            y += stack_height


def _insert_image_fit(slide: Slide, path: Path, left: int, top: int, max_width: int, max_height: int) -> Picture:
    """Insert `path` into the (left, top, max_width, max_height) box,
    preserving aspect ratio and centering it (never stretched)."""
    with Image.open(path) as im:
        img_w, img_h = im.size

    scale = min(max_width / img_w, max_height / img_h)
    fit_w, fit_h = int(img_w * scale), int(img_h * scale)
    fit_left = left + (max_width - fit_w) // 2
    fit_top = top + (max_height - fit_h) // 2
    return slide.shapes.add_picture(str(path), fit_left, fit_top, width=fit_w, height=fit_h)
