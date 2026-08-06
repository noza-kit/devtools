from pathlib import Path

import pytest

from slidecraft.parser import SlideParseError, parse_html


def test_parses_correct_number_of_slides(sample_html: Path):
    slides = parse_html(sample_html)
    assert len(slides) == 2


def test_title_extraction(sample_html: Path):
    slides = parse_html(sample_html)
    assert slides[0].title == "市場調査のサマリー"
    assert slides[1].title == "まとめ"


def test_bullet_bold_run(sample_html: Path):
    slides = parse_html(sample_html)
    item = slides[0].content_items[0]
    assert item.kind == "bullet"
    assert item.level == 0
    assert item.runs[0].text == "ターゲット層:"
    assert item.runs[0].bold is True
    assert item.runs[1].text == "20代〜30代の若年層"
    assert item.runs[1].bold is False


def test_bullet_italic_run(sample_html: Path):
    slides = parse_html(sample_html)
    item = slides[0].content_items[1]
    assert item.runs[0].text == "課題:"
    assert item.runs[0].italic is True


def test_nested_bullet_gets_incremented_level(sample_html: Path):
    slides = parse_html(sample_html)
    nested = slides[0].content_items[2]
    assert nested.kind == "bullet"
    assert nested.level == 1
    assert nested.runs[0].text == "SNS露出が競合より少ない"


def test_image_path_resolved_relative_to_html_file(sample_html: Path, sample_image: Path):
    slides = parse_html(sample_html)
    assert slides[0].images[0].path == sample_image.resolve()
    assert slides[0].images[0].alt == "年代別認知度グラフ"


def test_notes_extraction(sample_html: Path):
    slides = parse_html(sample_html)
    assert "重要なスライドです" in slides[0].notes


def test_missing_notes_is_empty_string(sample_html: Path):
    slides = parse_html(sample_html)
    assert slides[1].notes == ""


def test_paragraph_item(sample_html: Path):
    slides = parse_html(sample_html)
    para = slides[1].content_items[0]
    assert para.kind == "paragraph"
    assert para.runs[0].text == "今後のアクションプランについて説明します。"


def test_slide_without_content_div_falls_back_to_section(tmp_path: Path):
    html_path = tmp_path / "no_content_div.html"
    html_path.write_text(
        '<div class="presentation"><section class="slide"><h1>T</h1><ul><li>a</li></ul></section></div>',
        encoding="utf-8",
    )
    slides = parse_html(html_path)
    assert slides[0].title == "T"
    assert slides[0].content_items[0].runs[0].text == "a"


def test_slide_with_no_h1_has_empty_title(tmp_path: Path):
    html_path = tmp_path / "no_title.html"
    html_path.write_text(
        '<div class="presentation"><section class="slide"><div class="content"><p>x</p></div></section></div>',
        encoding="utf-8",
    )
    slides = parse_html(html_path)
    assert slides[0].title == ""


def test_no_slide_sections_raises(tmp_path: Path):
    html_path = tmp_path / "empty.html"
    html_path.write_text("<div>nothing here</div>", encoding="utf-8")
    with pytest.raises(SlideParseError):
        parse_html(html_path)


def test_multiple_images_on_one_slide(tmp_path: Path, sample_image: Path):
    html_path = tmp_path / "two_images.html"
    html_path.write_text(
        f"""<div class="presentation"><section class="slide"><h1>T</h1>
        <div class="content"><img src="{sample_image}"><img src="{sample_image}"></div>
        </section></div>""",
        encoding="utf-8",
    )
    slides = parse_html(html_path)
    assert len(slides[0].images) == 2
