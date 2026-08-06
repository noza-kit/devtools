from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image


@pytest.fixture
def sample_image(tmp_path: Path) -> Path:
    path = tmp_path / "images" / "graph1.png"
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (400, 300), (200, 50, 50)).save(path)
    return path


@pytest.fixture
def sample_html(tmp_path: Path, sample_image: Path) -> Path:
    html_path = tmp_path / "slides.html"
    html_path.write_text(
        """\
<div class="presentation">
  <section class="slide">
    <h1>市場調査のサマリー</h1>
    <div class="content">
      <ul>
        <li><strong>ターゲット層:</strong> 20代〜30代の若年層</li>
        <li><em>課題:</em> 認知度の低下が顕著
          <ul>
            <li>SNS露出が競合より少ない</li>
          </ul>
        </li>
      </ul>
      <img src="./images/graph1.png" alt="年代別認知度グラフ">
    </div>
    <aside class="notes">
      ここは重要なスライドです。特に若年層の認知度低下について強調してください。
    </aside>
  </section>
  <section class="slide">
    <h1>まとめ</h1>
    <div class="content">
      <p>今後のアクションプランについて説明します。</p>
      <ul>
        <li>施策A</li>
        <li>施策B</li>
      </ul>
    </div>
  </section>
</div>
""",
        encoding="utf-8",
    )
    return html_path
