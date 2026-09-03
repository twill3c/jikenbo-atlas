# web 配信用データのビルド(F-06 / F-07)
#
# data/raw + canon_cases.json + aozora_works.json →
#   web/data/stories/{work_id}.json  … パース済み本文(セグメント列。表示層まで無損失)
#   web/data/index.json              … 事件×作品の索引と統計
#
# data/pg + data/yaku + data/pg_sources.json →
#   web/data/taiyaku/{case_id}.json  … 英日対訳の行(F-16)。未訳段落は ja=null で明示する
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


def taiyaku_payload(pg, yaku, volume):
    """英日対訳の配信データ。原文段落と訳文を対にし、未訳は ja=null で明示する(F-16)。"""
    ja = {t["i"]: t["ja"] for t in yaku["paragraphs"]} if yaku else {}
    rows = [{"i": p["i"], "en": p["text"], "ja": ja.get(p["i"])} for p in pg["paragraphs"]]
    return {
        "case_id": pg["case_id"],
        "title_en": pg.get("title_en_display") or pg["title_en"],
        "n_paragraphs": len(rows),
        "n_translated": len(ja),
        "n_words": pg["n_words"],
        "source": {
            "ebook_id": pg["ebook_id"],
            "volume_title": pg["volume_title"],
            "url": volume["url"],
            "text_url": volume["text_url"],
            "fetched_at": volume["fetched_at"],
        },
        "translation": {
            "translator": yaku["translator"] if yaku else None,
            "model": yaku["model"] if yaku else None,
            "translated_at": yaku["translated_at"] if yaku else None,
        },
        "rows": rows,
    }


def build_taiyaku(out_dir):
    """data/pg + data/yaku → web/data/taiyaku/。{case_id: (段落数, 訳済み段落数)} を返す。"""
    pg_dir = ROOT / "data" / "pg"
    yaku_dir = ROOT / "data" / "yaku"
    sources_path = ROOT / "data" / "pg_sources.json"
    if not sources_path.exists() or not any(pg_dir.glob("*.json")):
        return {}
    volumes = {v["ebook_id"]: v for v in json.loads(
        sources_path.read_text(encoding="utf-8"))["volumes"]}
    out_dir.mkdir(parents=True, exist_ok=True)
    fill = {}
    for p in sorted(pg_dir.glob("*.json")):
        pg = json.loads(p.read_text(encoding="utf-8"))
        yp = yaku_dir / f"{pg['case_id']}.json"
        yaku = json.loads(yp.read_text(encoding="utf-8")) if yp.exists() else None
        payload = taiyaku_payload(pg, yaku, volumes[pg["ebook_id"]])
        (out_dir / f"{pg['case_id']}.json").write_text(
            json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        fill[pg["case_id"]] = payload
    return fill


def main():
    works = {w["work_id"]: w for w in json.loads(
        (ROOT / "data" / "aozora_works.json").read_text(encoding="utf-8"))["works"]}
    canon = json.loads((ROOT / "data" / "canon_cases.json").read_text(encoding="utf-8"))
    (OUT / "stories").mkdir(parents=True, exist_ok=True)
    taiyaku = build_taiyaku(OUT / "taiyaku")

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
        if c["id"] in taiyaku:
            t = taiyaku[c["id"]]
            entry["pg"] = {
                "ebook_id": t["source"]["ebook_id"],
                "n_paragraphs": t["n_paragraphs"],
                "n_translated": t["n_translated"],
                "n_words": t["n_words"],
            }
        index_cases.append(entry)

    shorts = [c for c in canon["cases"] if not c["is_novel"]]
    stats = {
        "n_cases": len(canon["cases"]),
        "n_shorts": len(shorts),
        "n_texts": n_texts,
        "n_no_death_shorts": sum(1 for c in shorts if not c["deaths"]),
        # 自前和訳層の充填率(F-15)。分子と分母の両方を出す — 途中でも
        # 「訳せた分だけ」と分かる状態で配る
        "n_pg_cases": len(taiyaku),
        "n_pg_paragraphs": sum(t["n_paragraphs"] for t in taiyaku.values()),
        "n_pg_translated": sum(t["n_translated"] for t in taiyaku.values()),
        "n_pg_cases_done": sum(1 for t in taiyaku.values()
                               if t["n_translated"] == t["n_paragraphs"]),
    }
    index = {"generated_at": canon["generated_at"], "cases": index_cases, "stats": stats}
    (OUT / "index.json").write_text(json.dumps(index, ensure_ascii=False), encoding="utf-8")
    print(f"stories: {n_texts} 件 / index: {len(index_cases)} 事件 → web/data/")
    if taiyaku:
        done = stats["n_pg_cases_done"]
        para, tr = stats["n_pg_paragraphs"], stats["n_pg_translated"]
        print(f"対訳: {stats['n_pg_cases']} 事件 / 訳了 {done} 事件 / "
              f"充填率 {tr}/{para} 段落({tr / para * 100:.1f}%) → web/data/taiyaku/")


if __name__ == "__main__":
    main()
