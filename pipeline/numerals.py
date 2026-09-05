# 英語原文と日本語訳文から「数」を取り出す(T-711 の道具)。
#
# ■ 再設計(2026-09-05)——曖昧なものは合成せず、捨てる
#
# 旧版は英語の数詞の並びを文法規則で合成していた。そのたびに現実の文が規則を破り、
# 例外を継ぎ足すことを 5 回繰り返した(nine-thirty / ten thirty-six / three-quarter /
# two and two / "at seven, one of the maids")。継ぎ足すほどゲートは発火しなくなるので、
# 前ループで「5 度目に緩めるなら作り直す」と決めていた。これがその作り直しである。
#
# 新しい方針は一つだけ:
#   **局所的に一義に決まるものだけを数として採り、決まらないものは黙って捨てる。**
#
#   - 算用数字はそのまま採る
#   - 数詞は「一語だけ孤立しているもの」と「twenty-six のような十位+一位の複合」だけ採る
#   - 数詞が二つ以上連なったら(nine thirty / two hundred and forty-five / seven one)
#     何を意味するか一義に決まらないので、その並びは丸ごと捨てる
#   - 並びは句読点で切れる。読点をまたいで数がつながることはない
#
# 捨てる側に倒したので分母は減るが、残った 1 件 1 件は「訳文にこの数が現れるはずだ」と
# 断言できるものになった。時刻の綴りを潰す特別扱い(_CLOCK)も and の位置規則も、
# この方針からは不要になって消えた。残った特別扱いは _NOT_NUMBER ただ一つで、
# これは文法規則ではなく「three-quarter は数ではない」という語彙の事実である。
#
# 較正で分かったこの道具の限界(実測 2026-09-04、旧版・訳了 11 篇 306 例):
#   - 外れを全数目視して**訳の誤りは 0 件**。残る外れは日本語として正しい訳しぶりが原因:
#       two arms → 両腕 / a day or two → 一両日 / Two can play at that game → お互いさま
#     日本語は対の身体部位や慣用句で数詞を落とす。これは是正できないし、すべきでもない
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

# 数詞の並びを取り出す。語と語をつなげるのは空白・ハイフン・and だけで、
# 読点や句点が入れば別の並びになる(旧版はここで読点を無視して 7+1=8 を作っていた)
_RUN = re.compile(
    r"\b(?:" + "|".join(sorted(_WORDS, key=len, reverse=True)) + r")"
    r"(?:[-\s]+(?:and[-\s]+)?(?:" + "|".join(sorted(_WORDS, key=len, reverse=True)) + r"))*\b",
    re.I)
_SPLIT = re.compile(r"[-\s]+(?:and[-\s]+)?", re.I)

# 数でない複合語。three-quarter はラグビーの位置(訳語は「スリー・クォーター」)で
# あって数詞ではない。実測 2026-09-05: MISS で 5 件をこれで誤検出していた。
# これは数詞の文法規則ではなく、語彙の事実に基づく唯一の特別扱い
_NOT_NUMBER = re.compile(
    r"\b(?:one|two|three|four)[-\s](?:quarter|quarters|half|halves)s?\b", re.I)

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


def _run_value(words):
    """数詞の並び一つを値にする。一義に決まらなければ None を返して捨てる。

    採るのは二通りだけ:
      - 語が一つ(seven / hundred / million)
      - 十位+一位の複合(twenty-six)。ハイフンでも空白でも同じ
    それ以外(nine thirty / two hundred and forty-five / seven one)は、
    時刻なのか合成数なのか隣の文の数なのかが文面だけでは決まらないので捨てる。
    """
    if len(words) == 1:
        w = words[0]
        return _ONES.get(w) or _TENS.get(w) or _SCALE.get(w)
    if len(words) == 2 and words[0] in _TENS and words[1] in _ONES and _ONES[words[1]] < 10:
        return _TENS[words[0]] + _ONES[words[1]]
    return None


def en_numbers(text):
    """原文に現れる数の値の集合。

    値 1 は数えない —— 冠詞・代名詞の one("one of the finest"、"no one")が
    大量に紛れ込み、較正では外れの過半を占めたため(実測 2026-09-04)。
    """
    text = _NOT_NUMBER.sub(" ", text)
    vals = set()
    for m in re.finditer(r"\d[\d,]*", text):
        vals.add(int(m.group().replace(",", "")))
    for m in _RUN.finditer(text):
        words = [w.lower() for w in _SPLIT.split(m.group()) if w]
        v = _run_value(words)
        if v is not None:
            vals.add(v)
    return {v for v in vals if v >= 2}
