# T-501..T-505(F-09 / F-10)— テキスト分析と人物ネットワークのゲート
#
# 較正ファースト(T-501): 抽出器を全編に展開する前に、実在行から作った小フィクスチャで
# 手で数えた正解と一致することを確認する(kyokai-lab の教訓)。
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent
ANALYSIS = ROOT / "web" / "data" / "analysis.json"
WORKS = ROOT / "data" / "aozora_works.json"
CANON = ROOT / "data" / "canon_cases.json"


@pytest.mark.unit
def test_t501_quote_extractor_calibration():
    from pipeline.analyze_text import quote_chars
    # 手計算の導出(実在行、赤毛連盟 2026-08-24 取得分より):
    #   「その通り。真っ最中だ。」 → 鉤括弧内は「その通り。真っ最中だ。」の中身 11 字
    #     (そ,の,通,り,。,真,っ,最,中,だ,。)
    assert quote_chars("「その通り。真っ最中だ。」") == 11
    #   地の文のみ → 0 字
    assert quote_chars("私は仕事の邪魔をしたと思い、詫びを入れてお暇しようとした。") == 0
    #   混在行: 「いや、実にいい頃合いだ、ワトソンくん。」(18字)+地の文
    #     (い,や,、,実,に,い,い,頃,合,い,だ,、,ワ,ト,ソ,ン,く,ん,。 = 19字)
    assert quote_chars("「いや、実にいい頃合いだ、ワトソンくん。」ホームズの声は、親しみに満ちていた。") == 19
    #   閉じ括弧のない行は行末まで台詞とみなす(方針)
    assert quote_chars("「未閉鎖の台詞") == 6


needs_analysis = pytest.mark.skipif(not ANALYSIS.exists(), reason="analysis 未生成")


@pytest.fixture(scope="module")
def analysis():
    return json.loads(ANALYSIS.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def works():
    return json.loads(WORKS.read_text(encoding="utf-8"))["works"]


@pytest.fixture(scope="module")
def cases():
    return json.loads(CANON.read_text(encoding="utf-8"))["cases"]


@needs_analysis
@pytest.mark.validation
def test_t502_coverage(analysis, works):
    expected = {str(w["work_id"]) for w in works if w["holmes"] is True}
    assert set(analysis["works"].keys()) == expected
    for wid, a in analysis["works"].items():
        assert 0 < a["quote_ratio"] < 1, wid
        assert a["chars"] > 0


@needs_analysis
@pytest.mark.validation
def test_t503_network(analysis, works, cases):
    wmap = {w["work_id"]: w for w in works}
    corpus_cases = {c["id"] for c in cases
                    if any(wmap[a["work_id"]]["holmes"] is True for a in c["aozora"])}
    # ホームズは全 corpus 事件に登場(holmes 判定の定義から導出される不変量)
    holmes_edges = {e["case_id"] for e in analysis["network"]["edges"] if e["char"] == "ホームズ"}
    assert holmes_edges == corpus_cases
    valid_chars = {c["name"] for c in analysis["network"]["chars"]}
    for e in analysis["network"]["edges"]:
        assert e["char"] in valid_chars
        assert e["case_id"] in corpus_cases
        assert e["count"] > 0


@needs_analysis
@pytest.mark.validation
def test_t504_translation_pairs(analysis, works, cases):
    wmap = {w["work_id"]: w for w in works}
    expected = {c["id"] for c in cases
                if sum(1 for a in c["aozora"] if not wmap[a["work_id"]].get("external_host")) >= 2}
    assert {p["case_id"] for p in analysis["pairs"]} == expected
    for p in analysis["pairs"]:
        assert len(p["works"]) >= 2


@pytest.mark.integration
def test_t505_lens_page():
    if not (ROOT / "web" / "lens.html").exists():
        pytest.fail("lens.html がない")
    html = (ROOT / "web" / "lens.html").read_text(encoding="utf-8")
    js = (ROOT / "web" / "lens.js").read_text(encoding="utf-8")
    for mount in ('id="network"', 'id="pairs"', 'id="ratios"'):
        assert mount in html
    assert "data/analysis.json" in js
