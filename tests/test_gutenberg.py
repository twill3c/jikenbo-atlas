# T-701..T-706(F-13 / F-14 / F-15 / F-16)— Project Gutenberg 原文層と自前和訳層
#
# 期待値の出所(HC-016):
#   T-701 分割の全単射   … 各巻自身の目次(Contents)。外部の作品リストを持ち込まない自己完結オラクル
#   T-702 対象事件の被覆 … canon_cases.json の「青空文庫の本文が無い事件」集合(実測から導く。定数で書かない)
#   T-703 往復           … 原文そのもの(自己完結オラクル)
#   T-704/705 訳の整合   … 原文の段落番号(実測)/ 字種は fleet 共通規範(キリル混入禁止)
#   T-706 充填率         … 実測。定数で書かず「分子 ≤ 分母」「index と実データが一致」の不変量で書く
import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent
PG_DIR = ROOT / "data" / "pg"
YAKU_DIR = ROOT / "data" / "yaku"
SOURCES = ROOT / "data" / "pg_sources.json"
CANON = ROOT / "data" / "canon_cases.json"
PG_CACHE = ROOT / "data" / "cache" / "pg"

needs_pg = pytest.mark.skipif(
    not SOURCES.exists() or not any(PG_DIR.glob("*.json")),
    reason="PG 原文未取得(pipeline/fetch_gutenberg.py → pipeline/pg_split.py を先に実行)",
)
needs_pg_cache = pytest.mark.skipif(
    not PG_CACHE.exists() or not any(PG_CACHE.glob("*.txt")),
    reason="PG 巻キャッシュ未取得(data/cache/ は git 管理外 — fetch_gutenberg.py を実行)",
)


def _cases_without_aozora():
    """青空文庫の本文が無い事件の id 集合。canon の実データから導く(定数で書かない)。"""
    canon = json.loads(CANON.read_text(encoding="utf-8"))
    return {c["id"] for c in canon["cases"] if not c.get("primary_work_id")}


@pytest.fixture(scope="module")
def sources():
    return json.loads(SOURCES.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def pg_works():
    return {p.stem: json.loads(p.read_text(encoding="utf-8")) for p in PG_DIR.glob("*.json")}


# ---- T-701: 目次を件数オラクルとした分割の全単射(F-14) ----

@pytest.mark.unit
def test_t701_split_headings_is_generic_not_hardcoded():
    """分割器は巻ごとの見出し正規表現を持たず、目次から解決する(HC-012「写さずに昇格」)。

    見出し形式は巻ごとに 6 種あった(実測 2026-09-04)。巻 ID を条件にした分岐で
    書き分けると、目次という自己完結オラクルを捨てて推測に戻ることになる。
    """
    src = (ROOT / "pipeline" / "pg_split.py").read_text(encoding="utf-8")
    for ebook_id in ("1661", "834", "108", "2350", "69700", "2097", "2852", "3289"):
        assert f'== {ebook_id}' not in src and f'"{ebook_id}":' not in src, \
            f"巻 {ebook_id} 専用の分岐が分割器にある"


@needs_pg
@pytest.mark.validation
def test_t701_contents_entries_resolve_bijectively(sources):
    """各巻: 目次項目数 == 解決した見出し数、かつ目次順に単調増加(取りこぼし・重複なし)。"""
    for s in sources["volumes"]:
        entries = s["contents"]
        resolved = s["resolved"]
        assert len(entries) == len(resolved), f"pg{s['ebook_id']}: 目次 {len(entries)} / 解決 {len(resolved)}"
        titles_in_contents = [e["title"] for e in entries]
        titles_resolved = [r["title"] for r in resolved]
        assert titles_in_contents == titles_resolved, f"pg{s['ebook_id']}: 目次順と解決順が違う"
        starts = [r["start_line"] for r in resolved]
        assert starts == sorted(starts), f"pg{s['ebook_id']}: 見出し行が目次順に並んでいない"
        assert len(set(starts)) == len(starts), f"pg{s['ebook_id']}: 見出し行の重複"


# ---- T-702: 対象 38 事件の被覆(F-14) ----

@needs_pg
@pytest.mark.validation
def test_t702_target_cases_all_have_source(pg_works):
    """青空文庫の本文が無い事件の集合 == PG 由来原文がある事件の集合(取りこぼし・余剰なし)。"""
    assert _cases_without_aozora() == set(pg_works)


@needs_pg
@pytest.mark.validation
def test_t702_provenance_recorded(sources, pg_works):
    """F-13 / N-03: 全巻に取得元 URL・取得日・sha256。各作品が実在の巻を指す。"""
    vol_ids = set()
    for s in sources["volumes"]:
        assert s["url"].startswith("https://www.gutenberg.org/")
        assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", s["fetched_at"])
        assert re.fullmatch(r"[0-9a-f]{64}", s["sha256"])
        vol_ids.add(s["ebook_id"])
    for cid, w in pg_works.items():
        assert w["ebook_id"] in vol_ids, cid
        assert w["paragraphs"], cid


# ---- T-703: 往復検査(F-14) ----

@needs_pg
@needs_pg_cache
@pytest.mark.validation
def test_t703_paragraphs_roundtrip_to_source_slice(sources, pg_works):
    """段落列 → 巻本文スライスの完全復元。原文そのものが正解(自己完結オラクル)。"""
    from pipeline.pg_split import join_paragraphs, read_volume

    vols = {s["ebook_id"]: s for s in sources["volumes"]}
    for cid, w in sorted(pg_works.items()):
        vol = vols[w["ebook_id"]]
        lines, eol = read_volume(w["ebook_id"])
        expected = eol.join(lines[w["start_line"]:w["end_line"]])
        assert join_paragraphs(w["paragraphs"], eol, w["tail_blanks"]) == expected, cid
        assert vol["ebook_id"] == w["ebook_id"]


# ---- T-704/705: 自前和訳層(F-15) ----

@needs_pg
@pytest.mark.validation
def test_t704_translation_indices_align_with_source(pg_works):
    """訳の段落番号は原文の段落番号の部分集合。抜け番・重複・空文字を許さない。"""
    for p in sorted(YAKU_DIR.glob("*.json")):
        y = json.loads(p.read_text(encoding="utf-8"))
        cid = y["case_id"]
        assert cid == p.stem
        assert cid in pg_works, f"{cid}: 対応する原文がない"
        n_src = len(pg_works[cid]["paragraphs"])
        idx = [t["i"] for t in y["paragraphs"]]
        assert len(set(idx)) == len(idx), f"{cid}: 段落番号の重複"
        assert all(0 <= i < n_src for i in idx), f"{cid}: 原文にない段落番号"
        assert idx == sorted(idx), f"{cid}: 段落番号が昇順でない"
        for t in y["paragraphs"]:
            assert t["ja"].strip(), f"{cid}#{t['i']}: 訳文が空"


@needs_pg
@pytest.mark.validation
def test_t704_translation_provenance():
    """F-15: 訳者・訳出日・モデルを明示する(既存の刊行訳の写しでないことを記録で示す)。"""
    for p in sorted(YAKU_DIR.glob("*.json")):
        y = json.loads(p.read_text(encoding="utf-8"))
        assert y["translator"], p.name
        assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", y["translated_at"]), p.name
        assert y["model"], p.name
        assert y["source"]["ebook_id"], p.name


@needs_pg
@pytest.mark.validation
def test_t705_translation_charset_hygiene():
    """訳文にキリル文字・ハングルが混入していない(fleet 共通規範 — 字形が似て目視で気づけない)。"""
    bad = re.compile(r"[Ѐ-ӿ가-힯]")
    for p in sorted(YAKU_DIR.glob("*.json")):
        y = json.loads(p.read_text(encoding="utf-8"))
        for t in y["paragraphs"]:
            m = bad.search(t["ja"])
            assert not m, f"{p.stem}#{t['i']}: 異種文字 {m.group()!r}"


@needs_pg
@pytest.mark.validation
def test_t705_translation_is_japanese():
    """訳文が日本語であること(かな・漢字を含む)。原文の貼り付け残りを弾く。"""
    ja = re.compile(r"[぀-ヿ一-鿿]")
    for p in sorted(YAKU_DIR.glob("*.json")):
        y = json.loads(p.read_text(encoding="utf-8"))
        for t in y["paragraphs"]:
            assert ja.search(t["ja"]), f"{p.stem}#{t['i']}: 日本語の文字がない"


# ---- T-706: 充填率と web への伝搬(F-15 / F-16) ----

@needs_pg
@pytest.mark.validation
def test_t706_fill_rate_matches_actual_data(pg_works):
    """index.json の充填率が実データと一致する。分子・分母の両方を持ち、分子 ≤ 分母。"""
    index = json.loads((ROOT / "web" / "data" / "index.json").read_text(encoding="utf-8"))
    by_id = {c["id"]: c for c in index["cases"]}
    for cid, w in sorted(pg_works.items()):
        pg = by_id[cid].get("pg")
        assert pg, f"{cid}: index.json に pg 情報がない"
        assert pg["n_paragraphs"] == len(w["paragraphs"]), cid
        yp = YAKU_DIR / f"{cid}.json"
        n_ja = len(json.loads(yp.read_text(encoding="utf-8"))["paragraphs"]) if yp.exists() else 0
        assert pg["n_translated"] == n_ja, cid
        assert pg["n_translated"] <= pg["n_paragraphs"], cid
    stats = index["stats"]
    assert stats["n_pg_paragraphs"] == sum(len(w["paragraphs"]) for w in pg_works.values())
    assert stats["n_pg_translated"] <= stats["n_pg_paragraphs"]


@pytest.mark.unit
def test_t706_taiyaku_page_skeleton():
    """F-16: 対訳ページの骨格(マウント要素・データ参照・表示切替)。"""
    html = (ROOT / "web" / "taiyaku.html").read_text(encoding="utf-8")
    js = (ROOT / "web" / "taiyaku.js").read_text(encoding="utf-8")
    for needle in ('id="t-title"', 'id="taiyaku-body"', "taiyaku.js", 'class="app-footer"'):
        assert needle in html, needle
    assert "data/taiyaku/" in js
    for mode in ("parallel", "alternate", "ja", "en"):
        assert mode in js, f"表示モード {mode} がない"


@needs_pg
@pytest.mark.validation
def test_t706_taiyaku_payloads_built(pg_works):
    """web/data/taiyaku/ に対象事件ぶんの配信データがあり、余剰がない(集合一致)。"""
    out = ROOT / "web" / "data" / "taiyaku"
    assert {p.stem for p in out.glob("*.json")} == set(pg_works)
    for p in sorted(out.glob("*.json")):
        d = json.loads(p.read_text(encoding="utf-8"))
        assert len(d["rows"]) == len(pg_works[p.stem]["paragraphs"])
        # 未訳段落は null で明示する(空文字で誤魔化さない — F-16)
        for r in d["rows"]:
            assert r["ja"] is None or r["ja"].strip()
        assert d["source"]["url"].startswith("https://www.gutenberg.org/")
