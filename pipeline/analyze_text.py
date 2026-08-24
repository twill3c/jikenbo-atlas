# テキスト分析(F-09 / F-10) — 台詞比率・人物言及・訳者ペア比較
#
# 方針:
#   - 台詞 = 「…」の中身。閉じ括弧のない行は行末まで台詞とみなす
#   - 人物の辺 = 本文実測(表記ゆれは 2026-08-24 の実測に基づく正規表現)。
#     ハドスン夫人は「ハド[ソス]ン夫人」限定 — GLOR の船員ハドソンとの同名誤帰属を防ぐ
#   - 対象は青空文庫収録の全テキスト。推定や正典知識による辺は作らない(実測のみ)
import json
import re
from pathlib import Path

try:
    from .aozora_parser import parse
except ImportError:  # スクリプト直接実行時
    from aozora_parser import parse

ROOT = Path(__file__).parent.parent
OUT = ROOT / "web" / "data"

CHARACTERS = [
    ("ホームズ", r"ホームズ"),
    ("ワトスン", r"ワト[ソス]ン|ウォトスン"),
    ("レストレード", r"レストレ[ーイ]?ド"),
    ("グレグスン", r"グレグ[ソス]ン"),
    ("マイクロフト", r"マイクロフト"),
    ("モリアーティ", r"モリア[ー]?ティ"),
    ("モラン", r"モラン"),
    ("ハドスン夫人", r"ハド[ソス]ン夫人"),
    ("ホプキンズ", r"ホプキン[ズス]"),
    ("ブラッドストリート", r"ブラッドストリ[ーイ]?ト"),
]

_QUOTE = re.compile(r"「([^」]*)」?")


def quote_chars(line):
    """行内の台詞(「…」の中身)文字数。閉じ無しは行末まで。"""
    return sum(len(m) for m in _QUOTE.findall(line))


def body_text(doc):
    """注記を除いた本文プレーンテキスト(ルビはベースのみ)を行リストで返す。"""
    lines = []
    for segs in doc.body:
        s = ""
        for seg in segs:
            if seg[0] == "text":
                s += seg[1]
            elif seg[0] == "ruby":
                s += seg[1]
        lines.append(s)
    return lines


def main():
    works = [w for w in json.loads((ROOT / "data" / "aozora_works.json").read_text(encoding="utf-8"))["works"]
             if w["holmes"] is True]
    cases = json.loads((ROOT / "data" / "canon_cases.json").read_text(encoding="utf-8"))["cases"]
    case_of = {a["work_id"]: c["id"] for c in cases for a in c["aozora"]}

    per_work = {}
    edge_counts = {}
    for w in works:
        raw = ROOT / "data" / "raw" / f"{w['work_id']:05d}.txt"
        with open(raw, encoding="utf-8", newline="") as f:
            doc = parse(f.read())
        lines = body_text(doc)
        text = "\n".join(lines)
        chars = sum(len(l) for l in lines)
        q = sum(quote_chars(l) for l in lines)
        ruby_n = sum(1 for segs in doc.body for seg in segs if seg[0] == "ruby")
        mentions = {}
        for name, pat in CHARACTERS:
            n = len(re.findall(pat, text))
            if n:
                mentions[name] = n
                cid = case_of[w["work_id"]]
                edge_counts[(name, cid)] = edge_counts.get((name, cid), 0) + n
        per_work[str(w["work_id"])] = {
            "title": w["title"],
            "translators": w["translators"],
            "case_id": case_of[w["work_id"]],
            "chars": chars,
            "quote_ratio": round(q / chars, 4),
            "ruby_per_1000": round(ruby_n / chars * 1000, 2),
            "mentions": mentions,
        }

    edges = [{"char": ch, "case_id": cid, "count": n}
             for (ch, cid), n in sorted(edge_counts.items())]
    chars_list = [{"name": name, "cases": sum(1 for (ch, _c) in edge_counts if ch == name)}
                  for name, _ in CHARACTERS if any(ch == name for (ch, _c) in edge_counts)]

    # 訳者ペア(同一事件に onsite 訳が 2 つ以上)
    by_case = {}
    for wid, a in per_work.items():
        by_case.setdefault(a["case_id"], []).append(int(wid))
    pairs = []
    for cid, wids in sorted(by_case.items()):
        if len(wids) >= 2:
            pairs.append({
                "case_id": cid,
                "works": [{"work_id": wid, **{k: per_work[str(wid)][k] for k in
                           ("title", "translators", "chars", "quote_ratio", "ruby_per_1000")}}
                          for wid in sorted(wids)],
            })

    out = {"generated_at": json.loads((ROOT / "data" / "aozora_works.json").read_text(encoding="utf-8"))["generated_at"],
           "works": per_work,
           "network": {"chars": chars_list, "edges": edges},
           "pairs": pairs}
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "analysis.json").write_text(json.dumps(out, ensure_ascii=False), encoding="utf-8")
    print(f"works {len(per_work)} / edges {len(edges)} / chars {len(chars_list)} / pairs {len(pairs)} → web/data/analysis.json")


if __name__ == "__main__":
    main()
