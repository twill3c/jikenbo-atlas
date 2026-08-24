# T-101..T-103(F-01 / F-02 / F-04)— 取得済みコーパス全体の validation
#
# data/raw/ と data/aozora_works.json が存在する環境でのみ実行(未取得なら skip)。
# 往復検査の正解は原文そのもの(自己完結オラクル)。
import json
from pathlib import Path

import pytest

from pipeline.aozora_parser import parse, serialize

ROOT = Path(__file__).parent.parent
RAW = ROOT / "data" / "raw"
WORKS = ROOT / "data" / "aozora_works.json"

pytestmark = pytest.mark.validation

needs_corpus = pytest.mark.skipif(
    not WORKS.exists() or not any(RAW.glob("*.txt")),
    reason="コーパス未取得(pipeline/fetch_aozora.py を先に実行)",
)


@pytest.fixture(scope="module")
def works():
    return json.loads(WORKS.read_text(encoding="utf-8"))


@needs_corpus
def test_t101_roundtrip_all():
    # F-04: 全取得テキストで serialize(parse(x)) == x。不一致 0 件
    failures = []
    for p in sorted(RAW.glob("*.txt")):
        with open(p, encoding="utf-8", newline="") as f:
            text = f.read()
        if serialize(parse(text)) != text:
            failures.append(p.name)
    assert failures == []


@needs_corpus
def test_t102_holmes_flag_resolved(works):
    # F-01: 全 work の holmes フラグが実測 evidence 付きで確定。needs_review 残 0。
    # aozora.gr.jp 外ホスト(external_host)のみ null(保留)を許す — SPEC F-01
    for w in works["works"]:
        if w.get("external_host"):
            assert w["holmes"] is None, w["title"]
        else:
            assert w["holmes"] in (True, False), w["title"]
        assert w.get("evidence"), w["title"]
        assert not w.get("needs_review"), w["title"]


@needs_corpus
def test_t102_downloaded_set_matches_holmes_set(works):
    # ホームズもの ⇔ data/raw に本文がある、の集合一致(取りこぼし・余剰なし)
    expected = {w["raw_path"] for w in works["works"] if w["holmes"]}
    actual = {f"data/raw/{p.name}" for p in RAW.glob("*.txt")}
    assert expected == actual


@needs_corpus
def test_t103_provenance(works):
    # F-02 / N-03: 全取得ファイルに取得元 URL と取得日
    for w in works["works"]:
        if w["holmes"]:
            assert w["zip_url"].startswith("https://www.aozora.gr.jp/cards/000009/files/")
            assert w["fetched_at"]
