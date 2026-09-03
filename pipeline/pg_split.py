# Project Gutenberg の巻を正典事件ごとの原文に分割する(F-14)
#
# 件数オラクルは各巻自身の目次(Contents)である。題名の推測で確定しない(HC-012)。
# 見出し形式は巻ごとに違った(実測 2026-09-04 — roman+ALLCAPS / roman+TitleCase /
# ALLCAPS 単独 / TitleCase 単独 / roman 行+ALLCAPS 行 / Chapter 行+TitleCase 行)。
# そこで巻 ID による分岐は持たず、「目次の各項目を、本文中で 1〜2 行の見出しとして
# 目次順に前方走査で解決する」という一本の手続きで全巻を扱う。
#
# 仮定が崩れたら落ちる検算(HC-075):
#   - 目次項目と解決した見出しが 1 対 1、かつ目次順に単調増加
#   - 見出しは前後を空行に挟まれている(地の文の一致を見出しと取り違えない)
#   - 計画(data/pg_plan.json)の title_en が実際の目次項目と一致する
#   - 段落列から巻本文スライスを完全復元できる(往復検査)
# いずれも満たさなければ例外を送出して止める。黙って違う結果を出す道を残さない。
import json
import re
import unicodedata
from pathlib import Path

ROOT = Path(__file__).parent.parent
CACHE = ROOT / "data" / "cache" / "pg"
PLAN = ROOT / "data" / "pg_plan.json"
OUT_DIR = ROOT / "data" / "pg"
SOURCES = ROOT / "data" / "pg_sources.json"

_START = re.compile(r"^\*\*\* START OF TH[EI]S? PROJECT GUTENBERG EBOOK")
_END = re.compile(r"^\*\*\* END OF TH[EI]S? PROJECT GUTENBERG EBOOK")
# 見出しの通番接頭辞: "Chapter I.", "Chapter 1", "PART II—", "XII.", "IV."
_PREFIX = re.compile(
    r"^\s*(?:(?:chapter|part)\s+)?(?:[0-9]+|[ivxlc]+)\s*[.—–\-]?\s*",
    re.I,
)
# 見出しの通番行と題名行の間に許す空行数(実測 2026-09-04: 事件簿は 1 行)
_HEADING_GAP = 2
# 裸の通番だけの行("XI"、"Chapter 4.")。作品の末尾がこれなら次の見出しが漏れている
_BARE_NUMBER = re.compile(r"^\s*(?:(?:chapter|part)\s+)?(?:[0-9]+|[ivxlc]+)\s*[.—–\-]?\s*$", re.I)


class SplitError(Exception):
    """分割の仮定が崩れたときに送出する。分類できなかったものを黙って捨てない。"""


def read_volume(ebook_id):
    """(行リスト, 改行コード) を返す。行末は取り除くが、改行コードは往復のため保持する。"""
    text = (CACHE / f"pg{ebook_id}.txt").read_text(encoding="utf-8", newline="")
    eol = "\r\n" if "\r\n" in text else "\n"
    return text.split(eol), eol


def norm_key(s):
    """比較用の正規化キー。曲線引用符・ダッシュ・大小・記号・空白の差を吸収する。"""
    s = unicodedata.normalize("NFKC", s)
    return re.sub(r"[^a-z0-9]+", "", s.lower())


def strip_prefix(s):
    return _PREFIX.sub("", s.strip(), count=1)


def body_range(lines):
    """PG の定型ヘッダ・フッタを除いた本文の行範囲 [start, end) を返す。"""
    start = end = None
    for i, l in enumerate(lines):
        if start is None and _START.match(l):
            start = i + 1
        elif _END.match(l):
            end = i
            break
    if start is None or end is None or end <= start:
        raise SplitError(f"PG の開始・終了マーカーを特定できない(start={start}, end={end})")
    return start, end


def find_contents(lines, start, end):
    """目次ブロックの項目リストと、目次が終わる行を返す。件数オラクルの出所。"""
    ci = None
    for i in range(start, min(start + 300, end)):
        if lines[i].strip().lower() == "contents":
            ci = i
            break
    if ci is None:
        raise SplitError("目次(Contents)が見つからない — 件数オラクルが取れない")
    entries, blank, last = [], 0, ci
    for i in range(ci + 1, min(ci + 120, end)):
        if lines[i].strip() == "":
            blank += 1
            if blank >= 3 and entries:
                break
            continue
        blank = 0
        entries.append({"title": lines[i].strip(), "line": i})
        last = i
    if not entries:
        raise SplitError("目次に項目がない")
    return entries, last


def _matches(window, entry_title):
    """1〜2 行の窓が目次項目の見出しとして一致するか。接頭辞の有無どちらでも認める。"""
    keys = {norm_key(entry_title), norm_key(strip_prefix(entry_title))} - {""}
    cands = {norm_key(window), norm_key(strip_prefix(window))}
    return bool(keys & cands)


def resolve_headings(lines, entries, search_from, end):
    """目次項目を本文中の見出しへ、目次順の前方走査で解決する。

    前方走査にするのは、同じ題が巻内に二度現れる場合があるため(実測 2026-09-04:
    恐怖の谷の "PART I—The Tragedy of Birlstone" と "Chapter III—The Tragedy of
    Birlstone")。目次の順序を使えば曖昧さが消える。
    """
    def blank(i):
        return i < 0 or i >= len(lines) or lines[i].strip() == ""

    resolved, cursor = [], search_from
    for e in entries:
        hit = None
        i = cursor
        while i < end:
            if lines[i].strip() == "" or not blank(i - 1):
                i += 1
                continue
            # 見出しは前後を空行に挟まれた 1〜2 行である、を走査の条件そのものにする。
            # 事後の assert にすると、地の文の誤一致でそこで止まってしまう(実測
            # 2026-09-04: バスカヴィル家の犬の行 1060 は "…Sir Henry Baskerville.”"
            # という台詞で、通番を落とした題名キーと一致する)。
            # 2 行窓を先に試すのは、通番と題名が別行に分かれる巻があるため
            # ("Chapter 4." + "Sir Henry Baskerville")。1 行窓を先に当てると起点が 1 行ずれる。
            # 窓は空行をまたげる — 通番と題名の間に空行を挟む巻がある(実測 2026-09-04:
            # 事件簿の "XI" / 空行 / "THE ADVENTURE OF SHOSCOMBE OLD PLACE")。
            # 隣接を前提にすると題名行だけを見出しにしてしまい、通番が前の篇の末尾に残る。
            j = i + 1
            while j < end and blank(j) and j - i <= _HEADING_GAP:
                j += 1
            if j < end and j > i and not blank(j) and blank(j + 1):
                two = lines[i].strip() + " " + lines[j].strip()
                if _matches(two, e["title"]):
                    hit = (i, j + 1)
                    break
            if blank(i + 1) and _matches(lines[i].strip(), e["title"]):
                hit = (i, i + 1)
                break
            i += 1
        if hit is None:
            raise SplitError(f"目次項目 {e['title']!r} に対応する見出しが本文にない")
        hs, he = hit
        resolved.append({"title": e["title"], "start_line": hs, "heading_end": he})
        cursor = he
    starts = [r["start_line"] for r in resolved]
    if starts != sorted(starts) or len(set(starts)) != len(starts):
        raise SplitError("見出しが目次順に単調増加していない")
    return resolved


def to_paragraphs(slice_lines):
    """空行区切りのブロックに分ける。先行空行数を持たせ、完全復元できるようにする。"""
    paragraphs, tail, buf, before = [], 0, [], 0
    for l in slice_lines:
        if l.strip() == "":
            if buf:
                paragraphs.append({"i": len(paragraphs), "before": before, "lines": buf})
                buf, before = [], 0
            before += 1
            continue
        buf.append(l)
    if buf:
        paragraphs.append({"i": len(paragraphs), "before": before, "lines": buf})
        before = 0
    tail = before
    for p in paragraphs:
        p["text"] = " ".join(x.strip() for x in p["lines"])
    return paragraphs, tail


def join_paragraphs(paragraphs, eol, tail_blanks=0):
    """段落列から巻本文スライスを復元する(往復検査 T-703 の逆写像)。"""
    out = []
    for p in paragraphs:
        out.extend([""] * p["before"])
        out.extend(p["lines"])
    out.extend([""] * tail_blanks)
    return eol.join(out)


def split_volume(vol):
    """1 巻を処理し、(sources 記録, {case_id: 作品ペイロード}) を返す。"""
    ebook_id = vol["ebook_id"]
    lines, eol = read_volume(ebook_id)
    bstart, bend = body_range(lines)
    entries, contents_end = find_contents(lines, bstart, bend)
    resolved = resolve_headings(lines, entries, contents_end + 1, bend)

    works = {}
    for w in vol["works"]:
        a, b = w["entries"]
        if not (1 <= a <= b <= len(entries)):
            raise SplitError(f"{w['case_id']}: 目次項目 {a}..{b} は範囲外(目次 {len(entries)} 項目)")
        # 計画の title_en が実際の目次項目と一致するかの検算(HC-075)。
        # 目次行は巻の通番("IV.", "Chapter 1")を伴うので、通番を落としたキーで比べる。
        actual = entries[a - 1]["title"]
        if not _matches(actual, w["title_en"]):
            raise SplitError(
                f"{w['case_id']}: 計画の題 {w['title_en']!r} が実際の目次項目 {actual!r} と違う")
        start = resolved[a - 1]["start_line"]
        end = resolved[b]["start_line"] if b < len(resolved) else bend
        paragraphs, tail = to_paragraphs(lines[start:end])
        if join_paragraphs(paragraphs, eol, tail) != eol.join(lines[start:end]):
            raise SplitError(f"{w['case_id']}: 段落分割が往復しない")
        # 末尾が裸の通番なら、次の見出しの一部を取り込んでいる(実測 2026-09-04 に
        # 事件簿で発生。全単射も往復も緑のまま通る欠陥なので、ここで別に止める)
        if paragraphs and _BARE_NUMBER.match(paragraphs[-1]["text"]):
            raise SplitError(
                f"{w['case_id']}: 末尾段落が裸の通番 {paragraphs[-1]['text']!r} — "
                "次の見出しを取り込んでいる")
        works[w["case_id"]] = {
            "case_id": w["case_id"],
            "ebook_id": ebook_id,
            "volume_title": vol["volume_title"],
            # title_en は目次の項目そのまま(照合の鍵)。表示には巻の通番を落としたものを使う
            "title_en": actual,
            "title_en_display": strip_prefix(actual).strip() or actual,
            "heading": resolved[a - 1]["title"],
            "start_line": start,
            "end_line": end,
            "tail_blanks": tail,
            "n_paragraphs": len(paragraphs),
            "n_words": sum(len(p["text"].split()) for p in paragraphs),
            "paragraphs": paragraphs,
        }
    return entries, resolved, works


def main():
    import hashlib
    from datetime import date

    today = date.today().isoformat()
    plan = json.loads(PLAN.read_text(encoding="utf-8"))
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    volumes, n_works = [], 0
    for vol in plan["volumes"]:
        entries, resolved, works = split_volume(vol)
        text = (CACHE / f"pg{vol['ebook_id']}.txt").read_text(encoding="utf-8", newline="")
        volumes.append({
            "ebook_id": vol["ebook_id"],
            "volume_title": vol["volume_title"],
            "url": f"https://www.gutenberg.org/ebooks/{vol['ebook_id']}",
            "text_url": f"https://www.gutenberg.org/cache/epub/{vol['ebook_id']}/pg{vol['ebook_id']}.txt",
            "fetched_at": today,
            "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
            "line_ending": "CRLF" if "\r\n" in text else "LF",
            "contents": entries,
            "resolved": resolved,
        })
        for cid, w in works.items():
            (OUT_DIR / f"{cid}.json").write_text(
                json.dumps(w, ensure_ascii=False, indent=1), encoding="utf-8")
        n_works += len(works)
        print(f"  pg{vol['ebook_id']:>5} 目次 {len(entries):>2} 項目 → 解決 {len(resolved):>2} / "
              f"採録 {len(works):>2} 事件  {vol['volume_title']}")
    SOURCES.write_text(json.dumps(
        {"note": "PG 巻の取得記録と、目次を件数オラクルとした見出し解決の結果(F-13/F-14)",
         "generated_at": today, "volumes": volumes},
        ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{n_works} 事件の原文 → data/pg/ / {len(volumes)} 巻の記録 → data/pg_sources.json")


if __name__ == "__main__":
    main()
