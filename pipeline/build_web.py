# web 配信用データのビルド(F-06 / F-07)
#
# data/raw + canon_cases.json + aozora_works.json →
#   web/data/stories/{work_id}.json  … パース済み本文(セグメント列。表示層まで無損失)
#   web/data/index.json              … 事件×作品の索引と統計
#
# 読了時間: 本文文字数(注記除く) / 500 字/分 を切り上げ。
import json
import math
from pathlib import Path

try:
    from .aozora_parser import parse
except ImportError:  # スクリプト直接実行時
    from aozora_parser import parse

ROOT = Path(__file__).parent.parent
OUT = ROOT / "web" / "data"


def story_payload(w, case_id):
    raw = ROOT / "data" / "raw" / f"{w['work_id']:05d}.txt"
    with open(raw, encoding="utf-8", newline="") as f:
        doc = parse(f.read())
    chars = 0
    body = []
    for line in doc.body:
        segs = []
        for seg in line:
            segs.append(list(seg))
            if seg[0] == "text":
                chars += len(seg[1])
            elif seg[0] == "ruby":
                chars += len(seg[1])
        body.append(segs)
    return {
        "work_id": w["work_id"],
        "title": w["title"],
        "translators": w["translators"],
        "case_id": case_id,
        "source": {"card_url": w["card_url"], "zip_url": w["zip_url"], "fetched_at": w["fetched_at"]},
        "header": doc.header_lines,
        "body": body,
        "footer": doc.footer_lines,
        "chars": chars,
        "reading_minutes": max(1, math.ceil(chars / 500)),
    }


def main():
    works = {w["work_id"]: w for w in json.loads(
        (ROOT / "data" / "aozora_works.json").read_text(encoding="utf-8"))["works"]}
    canon = json.loads((ROOT / "data" / "canon_cases.json").read_text(encoding="utf-8"))
    (OUT / "stories").mkdir(parents=True, exist_ok=True)

    n_texts = 0
    index_cases = []
    for c in canon["cases"]:
        iworks = []
        for a in c["aozora"]:
            w = works[a["work_id"]]
            external = bool(w.get("external_host"))
            iw = {
                "work_id": w["work_id"],
                "title": w["title"],
                "translators": w["translators"],
                "external": external,
            }
            if not external:
                p = story_payload(w, c["id"])
                (OUT / "stories" / f"{w['work_id']:05d}.json").write_text(
                    json.dumps(p, ensure_ascii=False), encoding="utf-8")
                iw["chars"] = p["chars"]
                iw["reading_minutes"] = p["reading_minutes"]
                n_texts += 1
            iworks.append(iw)
        entry = {k: c[k] for k in (
            "id", "title_en", "title_ja", "collection", "pub_year", "is_novel",
            "case_type", "deaths", "client", "motive", "region", "primary_work_id", "site")}
        entry["works"] = iworks
        index_cases.append(entry)

    shorts = [c for c in canon["cases"] if not c["is_novel"]]
    stats = {
        "n_cases": len(canon["cases"]),
        "n_shorts": len(shorts),
        "n_texts": n_texts,
        "n_no_death_shorts": sum(1 for c in shorts if not c["deaths"]),
    }
    index = {"generated_at": canon["generated_at"], "cases": index_cases, "stats": stats}
    (OUT / "index.json").write_text(json.dumps(index, ensure_ascii=False), encoding="utf-8")
    print(f"stories: {n_texts} 件 / index: {len(index_cases)} 事件 → web/data/")


if __name__ == "__main__":
    main()
