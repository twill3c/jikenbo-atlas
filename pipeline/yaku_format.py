# 自前和訳ファイル(data/yaku/*.json)の体裁を一つに決める。
#
# 置いた理由: 訳文の一括是正を json.dump(indent=2) でやったら、段落が一行ずつに
# 展開されて 3 ファイルだけ体裁が変わった(実測 2026-09-05、224 行 → 742 行)。
# 中身は正しいので検査は全部緑のまま、差分だけが読めなくなる。**体裁を人手に
# 委ねるとこうなる**ので、正しい形を関数一つに閉じ込め、検査から同じ関数を呼ぶ。
import json


def canonical_text(obj):
    """訳ファイル一つの正しい本文を組み立てて返す。

    段落は一行に一つ。差分が「どの段落を直したか」として読めることを優先する。
    """
    head = {k: v for k, v in obj.items() if k != "paragraphs"}
    lines = ["{"]
    for k, v in head.items():
        lines.append(f' {json.dumps(k, ensure_ascii=False)}: '
                     f'{json.dumps(v, ensure_ascii=False)},')
    lines.append(' "paragraphs": [')
    body = [f'  {json.dumps({"i": p["i"], "ja": p["ja"]}, ensure_ascii=False)}'
            for p in obj["paragraphs"]]
    lines.append(",\n".join(body))
    lines.append(" ]")
    lines.append("}")
    return "\n".join(lines) + "\n"


def normalize(path):
    """ファイルを正しい体裁に書き直す。中身は一字も変えない。"""
    obj = json.loads(path.read_text(encoding="utf-8"))
    text = canonical_text(obj)
    if path.read_text(encoding="utf-8") != text:
        path.write_text(text, encoding="utf-8", newline="\n")
        return True
    return False


if __name__ == "__main__":
    from pathlib import Path
    root = Path(__file__).resolve().parent.parent / "data" / "yaku"
    changed = [p.name for p in sorted(root.glob("*.json")) if normalize(p)]
    print(f"整形: {len(changed)} ファイル" + (f" — {', '.join(changed)}" if changed else ""))
