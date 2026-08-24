# T-001..T-005(F-03 / F-04)— 青空文庫記法パーサー
#
# フィクスチャ: tests/fixtures/akage_excerpt.txt
#   出所: 青空文庫 card8「赤毛連盟」大久保ゆう訳 ルビあり zip
#   https://www.aozora.gr.jp/cards/000009/files/8_ruby_31219.zip(2026-08-24 取得)
#   から実在行のみを抜粋(行内容は無改変)。期待値はすべて同日の実測。
from pathlib import Path

import pytest

from pipeline.aozora_parser import parse, serialize

FIXTURE = Path(__file__).parent / "fixtures" / "akage_excerpt.txt"


@pytest.fixture(scope="module")
def text():
    # newline="" で読み、CRLF を保存する
    with open(FIXTURE, encoding="utf-8", newline="") as f:
        return f.read()


@pytest.fixture(scope="module")
def doc(text):
    return parse(text)


def _ruby_pairs(doc):
    pairs = []
    for line in doc.body:
        for seg in line:
            if seg[0] == "ruby":
                # seg = ("ruby", base, ruby, explicit)
                pairs.append((seg[1], seg[2], seg[3]))
    return pairs


def _notes(doc):
    notes = []
    for line in doc.body:
        for seg in line:
            if seg[0] == "note":
                notes.append(seg[1])
    return notes


@pytest.mark.unit
def test_t001_header_body_footer_split(doc):
    # 実測 2026-08-24: ヘッダは罫線(----)2 本目まで。フッタは［＃本文終わり］以降
    assert doc.header_lines[0] == "赤毛連盟"
    assert doc.header_lines[-1].startswith("----")
    assert sum(1 for l in doc.header_lines if l.startswith("----")) == 2
    assert doc.footer_lines[0] == "［＃本文終わり］"
    assert any(l.startswith("翻訳の底本：") for l in doc.footer_lines)
    assert len(doc.body) > 0


@pytest.mark.unit
def test_t002_ruby_auto_base(doc):
    # 実測 2026-08-24: 漢字連続がベース。直前のひらがなで止まる
    pairs = {(b, r) for b, r, _ in _ruby_pairs(doc)}
    assert ("弁慶格子", "シェパド・チェック") in pairs
    assert ("褐色", "ドラッブ") in pairs      # 「あわい褐色《ドラッブ》」の「い」で停止
    assert ("中心区", "シティ") in pairs


@pytest.mark.unit
def test_t003_explicit_pipe_base(doc, text):
    # 実測 2026-08-24: 「狩猟｜鞭《べん》」— ｜ がベースを 鞭 に限定する
    explicit = {(b, r) for b, r, e in _ruby_pairs(doc) if e}
    assert ("鞭", "べん") in explicit
    # 再直列化で ｜ が復元される
    assert "狩猟｜鞭《べん》" in serialize(doc)


@pytest.mark.unit
def test_t004_notes_verbatim(doc):
    notes = _notes(doc)
    assert any("挿絵１（fig8_01.png" in n for n in notes)
    assert any("ここから２字下げ" in n for n in notes)
    assert any("ここで字下げ終わり" in n for n in notes)
    # verbatim: 全注記が ［＃ で始まり ］ で終わる
    assert all(n.startswith("［＃") and n.endswith("］") for n in notes)


@pytest.mark.unit
def test_t005_roundtrip(doc, text):
    # F-04: 全文一致(ヘッダ・フッタ・改行コード含む)
    assert serialize(doc) == text
