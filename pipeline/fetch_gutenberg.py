# Project Gutenberg からの正典英語原文の取得(F-13)
#
# 対象は data/pg_plan.json が挙げる 8 巻。青空文庫に本文が無い 38 事件を覆う。
#
# 負荷配慮(N-02 と同じ規律): HTTP 取得ごとに 1 秒以上空ける。User-Agent を明示する。
# 取得物は data/cache/pg/ に置き、再実行時はキャッシュを優先して再取得しない。
#
# 権利: ドイル(1930 年没)の正典は日本・米国とも保護期間が満了しており、PG 版は
# 自由に再利用できる。本プロジェクトが収載するのは PG の本文と、それを土台に
# 新たに起こした自前の和訳であり、保護期間内の既刊訳は一切参照・収載しない。
import hashlib
import json
import time
from datetime import date
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).parent.parent
CACHE = ROOT / "data" / "cache" / "pg"
PLAN = ROOT / "data" / "pg_plan.json"
UA = "jikenbo-atlas-builder (public-domain corpus study; twill3c@gmail.com)"


def volume_url(ebook_id):
    return f"https://www.gutenberg.org/cache/epub/{ebook_id}/pg{ebook_id}.txt"


def cache_path(ebook_id):
    return CACHE / f"pg{ebook_id}.txt"


def fetch_volume(ebook_id):
    """巻本文を取得して返す。キャッシュがあれば再取得しない(N-02)。"""
    p = cache_path(ebook_id)
    if p.exists():
        return p.read_text(encoding="utf-8", newline=""), False
    url = volume_url(ebook_id)
    time.sleep(1.2)
    with urlopen(Request(url, headers={"User-Agent": UA})) as r:
        raw = r.read()
    text = raw.decode("utf-8")
    CACHE.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8", newline="")
    return text, True


def main():
    today = date.today().isoformat()
    plan = json.loads(PLAN.read_text(encoding="utf-8"))
    for v in plan["volumes"]:
        text, fetched = fetch_volume(v["ebook_id"])
        sha = hashlib.sha256(text.encode("utf-8")).hexdigest()
        eol = "\r\n" if "\r\n" in text else "\n"
        mark = "取得" if fetched else "キャッシュ"
        print(f"  pg{v['ebook_id']:>5} {v['volume_title'][:40]:<42} "
              f"{len(text):>7} 字 eol={'CRLF' if eol == chr(13) + chr(10) else 'LF'} "
              f"sha={sha[:12]} ({mark})")
    print(f"{len(plan['volumes'])} 巻 → {CACHE}(取得日 {today})")


if __name__ == "__main__":
    main()
