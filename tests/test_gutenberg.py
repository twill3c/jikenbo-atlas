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
GLOSSARY = ROOT / "data" / "yaku_glossary.json"
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


@needs_pg
@pytest.mark.validation
def test_t709_no_publisher_back_matter_in_works(pg_works):
    """作品に巻末の非本文(奥付・区切り・著作一覧広告)が混じっていない。

    期待値の出所: 実測 2026-09-04。巻の最終篇は終端が PG の本文マーカーまで伸びるため、
    #69700 の RETI に 5 段落の巻末広告が入っていた。全単射(T-701)も往復(T-703)も
    緑のまま通る欠陥だったので、別の述語で止める。
    """
    markers = re.compile(
        r"^(Printed in Great Britain|By A\. CONAN DOYLE$|\*(\s+\*)+\s*$"
        r"|End of (the )?Project Gutenberg|Updated editions will replace)")
    hits = []
    for cid, w in sorted(pg_works.items()):
        for q in w["paragraphs"]:
            if markers.match(q["text"].strip()):
                hits.append(f"{cid}#{q['i']}: {q['text'][:60]!r}")
    assert hits == [], hits


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


# ---- T-710: 台詞の取りこぼし(F-15)----
#
# 原文の引用開始記号の数と、訳文の 「 の数を作品単位で比べる。照合の鍵は原文なので循環しない。
# 段落単位では入れ子や地の文への回収でずれるため、作品単位の比で見る。

_OPEN_EN = re.compile(r'(?:^|[\s(\[])["“]')


def _speech_ratio(yaku, pg):
    src = {q["i"]: q["text"] for q in pg["paragraphs"]}
    en = sum(len(_OPEN_EN.findall(src[t["i"]])) for t in yaku["paragraphs"])
    ja = sum(t["ja"].count("「") for t in yaku["paragraphs"])
    return en, ja


@needs_pg
@pytest.mark.validation
def test_t710_speech_is_not_dropped(pg_works):
    """作品単位で、訳文の鉤括弧の数が原文の引用符の数から大きく離れない。

    期待値の出所: 実測 2026-09-04。訳了 8 篇の作品別の比は 最小 0.994 / 最大 1.086
    (1.086 は入れ子の鉤括弧を持つ MUSG)。帯 [0.85, 1.25] は観測の外側に置いた番人で、
    正常な訳を落とすためではなく、台詞をまとめたり落としたりした状態を捕まえるためのもの。
    """
    LO, HI = 0.85, 1.25
    bad = []
    for p in sorted(YAKU_DIR.glob("*.json")):
        y = json.loads(p.read_text(encoding="utf-8"))
        pg = pg_works[y["case_id"]]
        # 部分訳では原文全体と比べられないので、全訳済みのみ対象
        if len(y["paragraphs"]) != len(pg["paragraphs"]):
            continue
        en, ja = _speech_ratio(y, pg)
        if en < 20:
            continue
        r = ja / en
        if not (LO <= r <= HI):
            bad.append(f"{p.stem}: 原文 {en} / 訳文 {ja}(比 {r:.3f})")
    assert bad == [], bad


@needs_pg
@pytest.mark.validation
def test_t710_gate_has_teeth(pg_works):
    """変異体でゲートが実際に火を噴くことを確かめる。

    このゲートは既存データでは最初から通るので、通ること自体は何も保証しない。
    「台詞を三つに一つ落とした訳」を作って食わせ、帯の外に出ることを確認する。
    """
    LO, HI = 0.85, 1.25
    p = next(iter(sorted(YAKU_DIR.glob("*.json"))))
    y = json.loads(p.read_text(encoding="utf-8"))
    pg = pg_works[y["case_id"]]

    en, ja = _speech_ratio(y, pg)
    assert LO <= ja / en <= HI, "前提: 元の訳は帯の中にある"

    # 変異体: 鉤括弧を三つに一つ取り除く(台詞を地の文に溶かした状態の代理)
    n = 0

    def drop(s):
        nonlocal n
        out = []
        for ch in s:
            if ch == "「":
                n += 1
                if n % 3 == 0:
                    continue
            out.append(ch)
        return "".join(out)

    mutant = {"paragraphs": [{"i": t["i"], "ja": drop(t["ja"])} for t in y["paragraphs"]]}
    _, ja2 = _speech_ratio(mutant, pg)
    assert ja2 < ja, "変異体で鉤括弧が減っていない"
    assert not (LO <= ja2 / en <= HI), \
        f"変異体({ja2}/{en} = {ja2 / en:.3f})が帯 [{LO}, {HI}] を出ない — ゲートが緩すぎる"


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


# ---- T-707: 訳語の一貫性(F-15)----
#
# オラクルの出所: 青空文庫の既存訳 29 テキストの全数実測(data/yaku_glossary.json)。
# 同じサイトの本文層(リーダー)と対訳層で人名の書き方が食い違うと、読者が別人と
# 取り違える。照合の鍵は**原文の英語名**なので、こちらの訳を正解に使う循環がない。

@pytest.fixture(scope="module")
def glossary():
    return json.loads(GLOSSARY.read_text(encoding="utf-8"))


@needs_pg
@pytest.mark.validation
def test_t707_forbidden_name_variants_absent(glossary, pg_works):
    """禁じた異表記が訳文に一つも現れない。"""
    hits = []
    for p in sorted(YAKU_DIR.glob("*.json")):
        y = json.loads(p.read_text(encoding="utf-8"))
        joined = "\n".join(t["ja"] for t in y["paragraphs"])
        for e in glossary["entries"]:
            for bad in e["forbidden"]:
                if bad in joined:
                    hits.append(f"{p.stem}: {bad!r}(基準は {e['ja']!r})")
    assert hits == [], hits


@needs_pg
@pytest.mark.validation
def test_t707_registered_rendering_used_where_source_has_name(glossary, pg_works):
    """原文にその名が繰り返し出る作品では、基準表記が訳文にも現れる。

    日本語は主語を落とすので段落ごとの対応は求めない。作品単位で、原文に 3 回以上
    現れる名は訳文にも現れる、という緩い不変量にする(訳し落としの取りこぼしを防ぐ)。
    """
    misses = []
    for p in sorted(YAKU_DIR.glob("*.json")):
        y = json.loads(p.read_text(encoding="utf-8"))
        src = "\n".join(q["text"] for q in pg_works[y["case_id"]]["paragraphs"])
        joined = "\n".join(t["ja"] for t in y["paragraphs"])
        # 訳が全段落そろっている作品だけを対象にする(部分訳では当然落ちる)
        if len(y["paragraphs"]) != len(pg_works[y["case_id"]]["paragraphs"]):
            continue
        for e in glossary["entries"]:
            if src.count(e["en"]) >= 3 and e["ja"] not in joined:
                misses.append(f"{p.stem}: 原文に {e['en']} が {src.count(e['en'])} 回あるが "
                              f"訳文に {e['ja']} がない")
    assert misses == [], misses


# ---- T-708: 訳し漏れの検出(F-15)----

@needs_pg
@pytest.mark.validation
def test_t708_no_truncated_paragraphs(pg_works):
    """段落の「日本語文字数 / 英語語数」比が下限を下回らない。

    期待値の出所: 実測 2026-09-04。自前訳 4 篇・10 語以上の 363 段落で
    最小 1.59 / p1 1.64 / 中央 2.28 / p95 3.00。**下限 1.20 は観測最小の下に置く** ——
    正常な訳を落とすためでなく、段落の一部しか訳していない(冒頭一文だけ等)状態を
    捕まえるための番人であり、その場合の比は 1 を大きく割る。
    """
    LOWER = 1.20
    thin = []
    for p in sorted(YAKU_DIR.glob("*.json")):
        y = json.loads(p.read_text(encoding="utf-8"))
        src = {q["i"]: q["text"] for q in pg_works[y["case_id"]]["paragraphs"]}
        for t in y["paragraphs"]:
            n_words = len(src[t["i"]].split())
            if n_words < 10:
                continue
            ratio = len(t["ja"]) / n_words
            if ratio < LOWER:
                thin.append(f"{p.stem}#{t['i']}: {n_words}語 → {len(t['ja'])}字(比 {ratio:.2f})")
    assert thin == [], thin


@needs_pg
@pytest.mark.validation
def test_t708_glossary_is_grounded_in_corpus(glossary):
    """訳語基準そのものが、青空文庫本文の実測に裏づけられている(思いつきで決めない)。"""
    raw = ROOT / "data" / "raw"
    if not any(raw.glob("*.txt")):
        pytest.skip("青空文庫コーパス未取得")
    corpus = "\n".join(p.read_text(encoding="utf-8", newline="") for p in raw.glob("*.txt"))
    for e in glossary["entries"]:
        n = corpus.count(e["ja"])
        assert n > 0, f"{e['ja']}: 既存訳に一度も現れない表記を基準にしている"
        for bad in e["forbidden"]:
            assert corpus.count(bad) < n, \
                f"{bad} が基準 {e['ja']} より多い({corpus.count(bad)} 対 {n})— 基準の取り違え"


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
