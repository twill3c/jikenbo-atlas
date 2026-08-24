# 青空文庫記法パーサー(F-03 / F-04)
#
# 保証: serialize(parse(text)) == text(全文一致)。
# ヘッダ(罫線 2 本目まで)とフッタ(［＃本文終わり］または 底本： 以降)は生のまま保持し、
# 本文のみをセグメント列(text / ruby / note)に構造化する。
#
# セグメント表現(タプル):
#   ("text", s)                       — 地の文
#   ("ruby", base, ruby, explicit)    — ルビ。explicit=True は ｜base《ruby》 由来
#   ("note", s)                       — 入力者注 ［＃…］ を verbatim 保持
import re
from dataclasses import dataclass, field

_DELIM = re.compile(r"^-{10,}$")
_FOOTER_HEADS = ("底本：", "底本:", "翻訳の底本：")

_TOKEN = re.compile(
    r"［＃[^］]*］"                     # 入力者注
    r"|｜([^｜《\r\n]*)《([^》]*)》"     # 明示ベースのルビ
    r"|《([^》]*)》"                    # 自動ベースのルビ
)

# ベース自動判定: 《 直前の文字と同じ文字クラスの連続を後ろから取る
_BASE_CLASSES = (
    r"[一-鿿㐀-䶿豈-﫿々〆〇ヵヶ]",  # 漢字・々〆〇
    r"[ァ-ヺー・]",                                          # カタカナ・長音
    r"[A-Za-z0-9Ａ-Ｚａ-ｚ０-９]",              # 英数(全半角)
    r"[ぁ-ゖゝゞ]",                                      # ひらがな
)
_BASE_RES = [re.compile(f"({c}+)$") for c in _BASE_CLASSES]


@dataclass
class Document:
    header_lines: list
    body: list
    footer_lines: list
    newline: str = "\r\n"


def _split_base(buf):
    """buf 末尾からルビのベースを切り出す。(残りテキスト, ベース) を返す。"""
    for rx in _BASE_RES:
        m = rx.search(buf)
        if m:
            return buf[: m.start(1)], m.group(1)
    if buf:
        return buf[:-1], buf[-1]
    return "", ""


def _parse_line(line):
    segs = []
    pos = 0
    buf = ""
    for m in _TOKEN.finditer(line):
        buf += line[pos : m.start()]
        tok = m.group(0)
        if tok.startswith("［＃"):
            if buf:
                segs.append(("text", buf))
                buf = ""
            segs.append(("note", tok))
        elif tok.startswith("｜"):
            if buf:
                segs.append(("text", buf))
                buf = ""
            segs.append(("ruby", m.group(1), m.group(2), True))
        else:
            rest, base = _split_base(buf)
            if rest:
                segs.append(("text", rest))
            segs.append(("ruby", base, m.group(3), False))
            buf = ""
        pos = m.end()
    buf += line[pos:]
    if buf:
        segs.append(("text", buf))
    return segs


def _serialize_line(segs):
    out = []
    for seg in segs:
        if seg[0] == "text" or seg[0] == "note":
            out.append(seg[1])
        else:
            _, base, ruby, explicit = seg
            out.append(("｜" if explicit else "") + base + "《" + ruby + "》")
    return "".join(out)


def parse(text):
    newline = "\r\n" if "\r\n" in text else "\n"
    lines = text.split(newline)

    # ヘッダ: 記号説明ブロックの罫線 2 本目まで(先頭 40 行以内に限る)
    delims = [i for i, l in enumerate(lines[:40]) if _DELIM.match(l)]
    header_end = delims[1] + 1 if len(delims) >= 2 else 0
    header_lines = lines[:header_end]

    # フッタ: ［＃本文終わり］があればそこから。なければ 底本：系の行から
    footer_start = len(lines)
    for i in range(header_end, len(lines)):
        if lines[i] == "［＃本文終わり］":
            footer_start = i
            break
    else:
        for i in range(len(lines) - 1, header_end - 1, -1):
            if lines[i].startswith(_FOOTER_HEADS):
                footer_start = i
                break

    body = [_parse_line(l) for l in lines[header_end:footer_start]]
    return Document(header_lines, body, lines[footer_start:], newline)


def serialize(doc):
    lines = list(doc.header_lines)
    lines.extend(_serialize_line(segs) for segs in doc.body)
    lines.extend(doc.footer_lines)
    return doc.newline.join(lines)
