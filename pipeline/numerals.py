# 英語原文と日本語訳文から「数」を取り出す(T-711 の道具)。
#
# 較正で分かったこの道具の限界(実測 2026-09-04、訳了 11 篇 306 例):
#   - 一致率 0.964、作品別 0.875〜1.000。外れ 11 件を全数目視して**訳の誤りは 0 件**
#   - 残る外れは日本語として正しい訳しぶりが原因である:
#       two arms → 両腕 / a day or two → 一両日 / Two can play at that game → お互いさま
#     日本語は対の身体部位や慣用句で数詞を落とすので、これは是正できないし、すべきでもない
#   - したがって T-711 の下限は「訳の忠実さ」ではなく「日本語の慣用」が決めている。
#     このゲートが捕まえるのは**系統的な数の破壊**であって、個々の訳し方の当否ではない
import re

_ONES = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7,
         "eight": 8, "nine": 9, "ten": 10, "eleven": 11, "twelve": 12, "thirteen": 13,
         "fourteen": 14, "fifteen": 15, "sixteen": 16, "seventeen": 17, "eighteen": 18,
         "nineteen": 19}
_TENS = {"twenty": 20, "thirty": 30, "forty": 40, "fifty": 50, "sixty": 60,
         "seventy": 70, "eighty": 80, "ninety": 90}
_SCALE = {"hundred": 100, "thousand": 1000, "million": 10 ** 6}
_WORDS = set(_ONES) | set(_TENS) | set(_SCALE)
_TOKEN = re.compile(r"[a-z]+", re.I)
# 時刻の綴り(nine-thirty など)。数詞の並びとして読むと 9+30=39 になるので先に潰す
_CLOCK = re.compile(
    r"\b(one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve)"
    r"[- ](five|ten|fifteen|twenty|twenty[- ]five|thirty|thirty[- ]five|forty|"
    r"forty[- ]five|fifty|fifty[- ]five)\b", re.I)

_K = {"〇": 0, "零": 0, "一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6,
      "七": 7, "八": 8, "九": 9}
_UNIT = {"十": 10, "百": 100, "千": 1000}
_BIG = {"万": 10 ** 4, "億": 10 ** 8}
_KANJI = "〇零一二三四五六七八九十百千万億"


def kanji_to_int(s):
    """漢数字を値にする。羅列読み(一九〇七)と位取り読み(二十三・五百)の両方。"""
    if not s:
        return None
    if all(c in _K for c in s):
        v = 0
        for c in s:
            v = v * 10 + _K[c]
        return v
    total = section = digit = 0
    for c in s:
        if c in _K:
            digit = _K[c]
        elif c in _UNIT:
            section += (digit or 1) * _UNIT[c]
            digit = 0
        elif c in _BIG:
            total += (section + digit) * _BIG[c]
            section = digit = 0
        else:
            return None
    return total + section + digit


def ja_numbers(text):
    """訳文に現れる数の値の集合(算用数字+漢数字)。"""
    vals = set()
    for m in re.finditer(r"\d[\d,]*", text):
        vals.add(int(m.group().replace(",", "")))
    for m in re.finditer(f"[{_KANJI}]+", text):
        v = kanji_to_int(m.group())
        if v is not None:
            vals.add(v)
    return vals


def en_numbers(text):
    """原文に現れる数の値の集合。

    値 1 は数えない —— 冠詞・代名詞の one("one of the finest"、"no one")が
    大量に紛れ込み、較正では外れの過半を占めたため(実測 2026-09-04)。
    数詞の並びの途中の and は許す(two hundred and forty-five → 245)。
    """
    text = _CLOCK.sub(" ", text)
    vals = set()
    for m in re.finditer(r"\d[\d,]*", text):
        vals.add(int(m.group().replace(",", "")))
    toks = [t.lower() for t in _TOKEN.findall(text)]
    i = 0
    while i < len(toks):
        if toks[i] not in _WORDS:
            i += 1
            continue
        j = i
        total = section = 0
        saw = False
        while j < len(toks):
            w = toks[j]
            if w == "and" and saw and j + 1 < len(toks) and toks[j + 1] in _WORDS:
                j += 1
                continue
            if w not in _WORDS:
                break
            saw = True
            if w in _ONES:
                section += _ONES[w]
            elif w in _TENS:
                section += _TENS[w]
            elif w == "hundred":
                section = (section or 1) * 100
            else:
                total += (section or 1) * _SCALE[w]
                section = 0
            j += 1
        vals.add(total + section)
        i = j
    return {v for v in vals if v >= 2}
