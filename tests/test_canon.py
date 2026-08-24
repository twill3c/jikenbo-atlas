# T-201..T-206(F-05)— 正典 60 事件メタデータの整合ゲート
#
# 外部権威(2026-08-24 参照): 正典の短編集構成と初出年。
#   https://en.wikipedia.org/wiki/Canon_of_Sherlock_Holmes
#   計数の流儀: 「ボール箱」は英国流に従い『最後の挨拶』に置く(回想 11・挨拶 8)
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent
CANON = ROOT / "data" / "canon_cases.json"
WORKS = ROOT / "data" / "aozora_works.json"

pytestmark = pytest.mark.integration

# 外部権威の定数(出典は冒頭コメント)
COLLECTION_SIZES = {
    "adventures": 12,
    "memoirs": 11,
    "return": 13,
    "his_last_bow": 8,
    "casebook": 12,
}
COLLECTION_YEARS = {
    "adventures": (1891, 1892),
    "memoirs": (1892, 1893),
    "return": (1903, 1904),
    "his_last_bow": (1892, 1917),
    "casebook": (1921, 1927),
}
NOVEL_YEARS = {"STUD": 1887, "SIGN": 1890, "HOUN": 1901, "VALL": 1914}

CASE_TYPES = {"殺人", "盗難・強盗", "恐喝", "失踪・捜索", "詐欺・偽装", "機密・スパイ", "怪事件", "その他"}
REGIONS = {"ロンドン", "ロンドン近郊", "地方", "海外"}


@pytest.fixture(scope="module")
def cases():
    return json.loads(CANON.read_text(encoding="utf-8"))["cases"]


@pytest.fixture(scope="module")
def works():
    return json.loads(WORKS.read_text(encoding="utf-8"))["works"]


def test_t201_composition(cases):
    ids = [c["id"] for c in cases]
    assert len(ids) == len(set(ids))
    novels = [c for c in cases if c["is_novel"]]
    shorts = [c for c in cases if not c["is_novel"]]
    assert len(novels) == 4 and len(shorts) == 56
    by_col = {}
    for c in shorts:
        by_col[c["collection"]] = by_col.get(c["collection"], 0) + 1
    assert by_col == COLLECTION_SIZES


def test_t202_publication_years(cases):
    for c in cases:
        if c["is_novel"]:
            assert c["pub_year"] == NOVEL_YEARS[c["id"]], c["id"]
        else:
            lo, hi = COLLECTION_YEARS[c["collection"]]
            assert lo <= c["pub_year"] <= hi, c["id"]


def test_t203_vocab_and_required(cases):
    for c in cases:
        assert c["case_type"] in CASE_TYPES, c["id"]
        assert c["region"] in REGIONS, c["id"]
        assert isinstance(c["deaths"], bool), c["id"]
        for k in ("title_en", "title_ja", "client", "motive"):
            assert c.get(k), (c["id"], k)
        assert c.get("confidence") in ("high", "check"), c["id"]


def test_t204_corpus_bijection(cases, works):
    canon_wids = [a["work_id"] for c in cases for a in c["aozora"]]
    assert len(canon_wids) == len(set(canon_wids))  # 1 work は 1 事件にのみ属す
    expected = {w["work_id"] for w in works if w["holmes"] is True or w.get("external_host")}
    assert set(canon_wids) == expected


def test_t205_mapping_evidence(cases):
    for c in cases:
        for a in c["aozora"]:
            ev = a["evidence"]
            if ev.startswith("header:"):
                quoted = ev.split(":", 1)[1]
                raw = ROOT / "data" / "raw" / f"{a['work_id']:05d}.txt"
                if not raw.exists():
                    pytest.skip("コーパス未取得")
                with open(raw, encoding="utf-8", newline="") as f:
                    head = f.read().split("\r\n")[:6]
                assert quoted in head, (c["id"], a["work_id"])
            else:
                assert ev.startswith(("本文実測:", "題名対応(取得不能)")), (c["id"], a["work_id"])


def test_t206_primary_prefers_okubo(cases, works):
    wmap = {w["work_id"]: w for w in works}
    for c in cases:
        onsite = [a["work_id"] for a in c["aozora"] if not wmap[a["work_id"]].get("external_host")]
        if not onsite:
            assert c["primary_work_id"] is None, c["id"]
            continue
        assert c["primary_work_id"] in onsite, c["id"]
        okubo = [w for w in onsite if any("大久保" in t for t in wmap[w]["translators"])]
        if okubo:
            assert c["primary_work_id"] in okubo, c["id"]
