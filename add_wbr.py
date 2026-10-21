"""HTML内の日本語テキストに、BudouX で求めた文節の区切りごとに <wbr> を入れる。

Safari は word-break: auto-phrase に対応していないため、
「keep-all（勝手に改行しない）＋ <wbr>（ここなら改行してよい）」で同じ効果を出す。
<wbr> は white-space: nowrap の中でも改行させてしまうので、
改行させたくない要素（.nw / .btn / nowrap 指定など）の中には入れない。
何度実行しても同じ結果になるよう、最初に既存の <wbr> を取り除く。
"""
import re
import sys

import budoux

parser = budoux.load_default_japanese_parser()
JA = re.compile(r'[぀-ヿ㐀-鿿＀-￯]')
SKIP_TAGS = {'script', 'style', 'title', 'option', 'textarea', 'button'}
VOID = {'br', 'wbr', 'img', 'input', 'meta', 'link', 'hr', 'source'}
NOWRAP = re.compile(r'class="[^"]*\b(nw|btn|hd-entry|hd-logo|hd-sub)\b|white-space:\s*nowrap')
ENTITY = re.compile(r'(&#?\w+;)')


# BudouX が不自然な位置で区切ってしまう語の補正（目視で確認したもの）
FIXUPS = [
    ('部<wbr>門責任者', '部門責任者'),
    ('バック<wbr>ヤード', 'バックヤード'),
    ('サービスと<wbr>して', 'サービスとして'),
    ('考慮の<wbr>上', '考慮の上'),
    ('方<wbr>へ', '方へ'),
    ('方<wbr>のみ', '方のみ'),
    ('の<wbr>ため', 'のため'),
    ('イベントの<wbr>概要', 'イベントの概要'),
    ('<wbr>・', '・'),  # 「・」から行が始まらないようにする
]


def phrase(text):
    if not JA.search(text):
        return text
    out = []
    for part in ENTITY.split(text):
        if ENTITY.fullmatch(part) or not part:
            out.append(part)
        else:
            out.append('<wbr>'.join(parser.parse(part)))
    result = ''.join(out)
    for bad, good in FIXUPS:
        result = result.replace(bad, good)
    return result


def process(html):
    html = html.replace('<wbr>', '')
    tokens = re.split(r'(<[^>]+>)', html)
    stack = []  # (tag, この要素の中では <wbr> を入れないか)
    for i, tok in enumerate(tokens):
        if tok.startswith('<!--'):
            continue
        if tok.startswith('<'):
            m = re.match(r'<(/?)([a-zA-Z0-9]+)', tok)
            if not m:
                continue
            closing, tag = m.group(1), m.group(2).lower()
            if tag in VOID or tok.endswith('/>'):
                continue
            if closing:
                while stack and stack.pop()[0] != tag:
                    pass
            else:
                stack.append((tag, tag in SKIP_TAGS or bool(NOWRAP.search(tok))))
        elif not any(skip for _, skip in stack):
            tokens[i] = phrase(tok)
    return ''.join(tokens)


for path in sys.argv[1:]:
    src = open(path, encoding='utf-8').read()
    # <head> 内（title や meta の説明文）は触らず、<body> 以降だけ処理する
    head, sep, body = src.partition('<body>')
    result = head + sep + process(body)
    open(path, 'w', encoding='utf-8').write(result)
    print(path, 'wbr:', result.count('<wbr>'))
