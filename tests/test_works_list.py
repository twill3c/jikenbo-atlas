# T-006(F-01)— 作家ページからの作品リスト抽出
#
# フィクスチャ: tests/fixtures/person9.html
#   出所: https://www.aozora.gr.jp/index_pages/person9.html(2026-08-24 取得、無改変)
# 件数は定数で書かない(HC-016)。「公開中の <ol> 内 li との全単射」という不変量で検査する。
import re
from pathlib import Path

import pytest

from pipeline.fetch_aozora import parse_person_page

FIXTURE = Path(__file__).parent / "fixtures" / "person9.html"


@pytest.fixture(scope="module")
def html():
    return FIXTURE.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def works(html):
    return parse_person_page(html)


@pytest.mark.unit
def test_t006_bijection_with_li(html, works):
    sec = html.split("公開中の作品</a></h2>")[1].split("作業中の作品")[0]
    li_count = len(re.findall(r"<li>", sec))
    assert li_count > 0
    assert len(works) == li_count  # 取りこぼし・水増しなし


@pytest.mark.unit
def test_t006_invariants(works):
    ids = [w["work_id"] for w in works]
    assert len(ids) == len(set(ids))  # work_id 一意
    for w in works:
        assert w["title"]
        assert re.fullmatch(r"https://www\.aozora\.gr\.jp/cards/000009/card\d+\.html", w["card_url"])
        assert len(w["translators"]) >= 1


@pytest.mark.unit
def test_t006_known_anchor(works):
    # 実測 2026-08-24: 作品ID 8 = 赤毛連盟、訳者に大久保ゆうを含む
    w = {x["work_id"]: x for x in works}[8]
    assert w["title"] == "赤毛連盟"
    assert any("大久保" in t for t in w["translators"])
