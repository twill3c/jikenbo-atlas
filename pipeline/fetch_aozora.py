# 青空文庫からのドイル作品実測・取得(F-01 / F-02)
#
# 手順:
#   1. 作家ページ(person9)から「公開中の作品」全カードを抽出
#   2. 各カードページから「ルビあり」zip の URL を特定し取得
#   3. 本文を cp932 → UTF-8 で保存。ホームズ判定は本文実測(『ホームズ』出現)で確定(HC-012)
#      ホームズもののみ data/raw/ に置き、挿絵 PNG は data/raw/images/{work_id}/ へ
#   4. 一覧+provenance を data/aozora_works.json に書き出す
#
# 負荷配慮(N-02): HTTP 取得ごとに 1 秒以上空ける。取得物は data/cache/ に置き、
# 再実行時はキャッシュを優先して再取得しない。
import io
import json
import re
import time
import zipfile
from datetime import date
from pathlib import Path
from urllib.parse import urljoin
from urllib.request import Request, urlopen

ROOT = Path(__file__).parent.parent
CACHE = ROOT / "data" / "cache"
RAW = ROOT / "data" / "raw"
PERSON_URL = "https://www.aozora.gr.jp/index_pages/person9.html"
UA = "jikenbo-atlas-builder (aozora corpus study; twill3c@gmail.com)"

_LI = re.compile(r"<li>(.*?)</li>", re.S)
_CARD = re.compile(r'href="\.\./cards/000009/card(\d+)\.html">([^<]+)</a>')
_TRANS = re.compile(r'<a href="person\d+\.html">([^<]+)</a>')
_ZIP = re.compile(r'href="([^"]+\.zip)"')


def _http_get(url):
    time.sleep(1.2)
    with urlopen(Request(url, headers={"User-Agent": UA})) as r:
        return r.read()


def _cached_get(url, cache_name):
    p = CACHE / cache_name
    if p.exists():
        return p.read_bytes()
    data = _http_get(url)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(data)
    return data


def parse_person_page(html):
    sec = html.split("公開中の作品</a></h2>")[1].split("作業中の作品")[0]
    works = []
    for li in _LI.findall(sec):
        m = _CARD.search(li)
        if not m:
            continue
        works.append({
            "work_id": int(m.group(1)),
            "title": m.group(2).strip(),
            "card_url": f"https://www.aozora.gr.jp/cards/000009/card{m.group(1)}.html",
            "translators": [t.strip() for t in _TRANS.findall(li)],
        })
    return works


def find_ruby_zip(card_html, card_url):
    """aozora.gr.jp 上の zip URL を返す。全 zip が外部ホストなら ("external", 外部URL)。"""
    urls = [urljoin(card_url, u) for u in _ZIP.findall(card_html)]
    onsite = [u for u in urls if u.startswith("https://www.aozora.gr.jp/")]
    if not onsite:
        return ("external", urls[0]) if urls else (None, None)
    ruby = [u for u in onsite if "ruby" in u]
    return ("onsite", (ruby or onsite)[0])


def main():
    today = date.today().isoformat()
    RAW.mkdir(parents=True, exist_ok=True)
    person_html = _cached_get(PERSON_URL, "person9.html").decode("utf-8")
    works = parse_person_page(person_html)
    print(f"公開中の作品: {len(works)} 件")

    for w in works:
        card_html = _cached_get(w["card_url"], f"card{w['work_id']}.html").decode("utf-8")
        kind, zip_url = find_ruby_zip(card_html, w["card_url"])
        w["zip_url"] = zip_url
        if kind == "external":
            w["holmes"] = None
            w["external_host"] = True
            w["needs_review"] = False
            w["evidence"] = f"ファイルが aozora.gr.jp 外にホスト({zip_url})。本文取得不能のため判定保留(実測 {today})"
            print(f"  EXTERN {w['title']}({'、'.join(w['translators'])})")
            continue
        if kind is None:
            # 実測 2026-08-24: card535 はカード上に zip が無く外部サイト公開のみ
            w["holmes"] = None
            w["external_host"] = True
            w["needs_review"] = False
            w["evidence"] = f"カード上に取得可能な zip がない(外部サイト公開作品)。判定保留(実測 {today})"
            print(f"  EXTERN {w['title']}({'、'.join(w['translators'])}) zip なし")
            continue

        zdata = _cached_get(zip_url, zip_url.rsplit("/", 1)[1])
        zf = zipfile.ZipFile(io.BytesIO(zdata))
        txt_names = [n for n in zf.namelist() if n.lower().endswith(".txt")]
        if len(txt_names) != 1:
            w["holmes"] = None
            w["needs_review"] = True
            w["evidence"] = f"txt メンバーが 1 つでない: {txt_names}"
            print(f"  !! txt 異常: {w['title']} {txt_names}")
            continue
        text = zf.read(txt_names[0]).decode("cp932")

        n = text.count("ホームズ")
        w["holmes"] = n > 0
        w["needs_review"] = False
        w["evidence"] = f"本文中『ホームズ』{n} 回(実測 {today})"
        w["txt_name"] = txt_names[0]
        w["fetched_at"] = today

        if w["holmes"]:
            raw_name = f"{w['work_id']:05d}.txt"
            w["raw_path"] = f"data/raw/{raw_name}"
            with open(RAW / raw_name, "w", encoding="utf-8", newline="") as f:
                f.write(text)
            imgs = [n2 for n2 in zf.namelist() if n2.lower().endswith((".png", ".jpg"))]
            if imgs:
                img_dir = RAW / "images" / f"{w['work_id']:05d}"
                img_dir.mkdir(parents=True, exist_ok=True)
                for n2 in imgs:
                    (img_dir / Path(n2).name).write_bytes(zf.read(n2))
            w["n_images"] = len(imgs)
        print(f"  {'HOLMES' if w['holmes'] else '  --  '} {w['title']}({'、'.join(w['translators'])}) {w['evidence']}")

    out = {
        "source_url": PERSON_URL,
        "generated_at": today,
        "works": works,
    }
    (ROOT / "data" / "aozora_works.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    n_h = sum(1 for w in works if w["holmes"])
    n_r = sum(1 for w in works if w.get("needs_review"))
    print(f"ホームズもの {n_h} 件 / needs_review {n_r} 件 → data/aozora_works.json")


if __name__ == "__main__":
    main()
