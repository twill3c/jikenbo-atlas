# T-601(F-12)— kiko-atlas 準拠の下部固定フッタ
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent
PAGES = ["index.html", "map.html", "lens.html", "reader.html", "taiyaku.html"]
LINKS = [
    "https://claude.ai/code/artifact/b86e776b-0192-4883-8d22-09c72c272e27",  # 歩き方
    "https://claude.ai/code/artifact/f86403ca-7333-45a6-839f-3c2a25de6cc7",  # 設計図
    "https://github.com/twill3c/jikenbo-atlas",
    "https://app-menu-amber.vercel.app/",
]

pytestmark = pytest.mark.integration


def test_t601_footer_on_all_pages():
    for page in PAGES:
        html = (ROOT / "web" / page).read_text(encoding="utf-8")
        assert 'class="app-footer"' in html, page
        for link in LINKS:
            assert link in html, (page, link)


def test_t601_footer_fixed_css():
    css = (ROOT / "web" / "style.css").read_text(encoding="utf-8")
    assert ".app-footer" in css
    assert "position: fixed" in css
    assert "--footer-h" in css  # 本文が隠れない逃げ(body padding-bottom)に使われる
