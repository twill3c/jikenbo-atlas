# T-301..T-304(F-06 / F-07)— web ビルド成果物の整合
#
# オラクル: T-302 は「story JSON → 青空記法再構成 == パーサー serialize の本文」
# という自己完結の可逆性検査(表示層まで無損失であることの保証)。
import json
from pathlib import Path

import pytest

from pipeline.aozora_parser import parse, _serialize_line

ROOT = Path(__file__).parent.parent
STORIES = ROOT / "web" / "data" / "stories"
INDEX = ROOT / "web" / "data" / "index.json"
WORKS = ROOT / "data" / "aozora_works.json"
CANON = ROOT / "data" / "canon_cases.json"

pytestmark = pytest.mark.validation

needs_build = pytest.mark.skipif(
    not INDEX.exists(), reason="web 未ビルド(pipeline/build_web.py を先に実行)"
)


@pytest.fixture(scope="module")
def works():
    return json.loads(WORKS.read_text(encoding="utf-8"))["works"]


@pytest.fixture(scope="module")
def cases():
    return json.loads(CANON.read_text(encoding="utf-8"))["cases"]


@pytest.fixture(scope="module")
def index():
    return json.loads(INDEX.read_text(encoding="utf-8"))


@needs_build
def test_t301_story_coverage(works):
    expected = {f"{w['work_id']:05d}.json" for w in works if w["holmes"] is True}
    actual = {p.name for p in STORIES.glob("*.json")}
    assert actual == expected


@needs_build
def test_t302_story_lossless(works):
    for w in works:
        if w["holmes"] is not True:
            continue
        raw = (ROOT / "data" / "raw" / f"{w['work_id']:05d}.txt")
        with open(raw, encoding="utf-8", newline="") as f:
            doc = parse(f.read())
        story = json.loads((STORIES / f"{w['work_id']:05d}.json").read_text(encoding="utf-8"))
        rebuilt = [_serialize_line([tuple(s) for s in line]) for line in story["body"]]
        original = [_serialize_line(line) for line in doc.body]
        assert rebuilt == original, w["title"]


@needs_build
def test_t303_index_consistency(index, cases, works):
    assert {c["id"] for c in index["cases"]} == {c["id"] for c in cases}
    wmap = {w["work_id"]: w for w in works}
    n_works = 0
    for c in index["cases"]:
        for iw in c["works"]:
            n_works += 1
            assert iw["work_id"] in wmap
            if not iw["external"]:
                assert iw["reading_minutes"] > 0
                assert iw["chars"] > 0
    expected_total = sum(1 for w in works if w["holmes"] is True or w.get("external_host"))
    assert n_works == expected_total
    s = index["stats"]
    assert s["n_cases"] == len(cases)
    assert s["n_texts"] == sum(1 for w in works if w["holmes"] is True)


@needs_build
def test_t304_web_skeleton():
    idx = (ROOT / "web" / "index.html").read_text(encoding="utf-8")
    rdr = (ROOT / "web" / "reader.html").read_text(encoding="utf-8")
    for mount in ('id="stats"', 'id="charts"', 'id="filters"', 'id="case-list"'):
        assert mount in idx
    for mount in ('id="reader-body"', 'id="reader-head"'):
        assert mount in rdr
    # データパス参照は各ページが読み込む JS 側にある
    app = (ROOT / "web" / "app.js").read_text(encoding="utf-8")
    rjs = (ROOT / "web" / "reader.js").read_text(encoding="utf-8")
    assert "app.js" in idx and "data/index.json" in app
    assert "reader.js" in rdr and "data/stories/" in rjs
