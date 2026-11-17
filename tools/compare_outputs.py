#!/usr/bin/env python3
"""
Сравнение двух HTML-результатов после нормализации (без внешних библиотек).

Зачем: «повторяемость» это не побайтовое равенство. Два независимых вызова могут отличаться пробелами,
комментариями и метаданными. Инструмент убирает это и показывает, остались ли различия по существу.

Нормализация:
  * переводы строк к \\n, пробелы и пустые строки схлопываются;
  * HTML-комментарии удаляются;
  * элементы с атрибутом data-volatile удаляются целиком (время, идентификаторы запуска и т.п.);
  * <meta name="generator|generated|date"> удаляются;
  * числа в атрибутах id вида id-12345678 (случайные суффиксы) не нормализуются: это дефект, а не шум.

Запуск:  python3 tools/compare_outputs.py a.html b.html [--show-diff]
Код возврата: 0 нормализованные файлы равны; 1 различаются; 2 неверный ввод.
"""
import argparse, difflib, hashlib, re, sys

def _protect_raw(html):
    """Спрятать содержимое script/style/pre/textarea: пробелы внутри него значимы (V-02)."""
    store = []
    def repl(m):
        store.append(m.group(0)); return f'\x00{len(store) - 1}\x00'
    return re.sub(r'<(script|style|pre|textarea)\b[^>]*>.*?</\1\s*>', repl, html, flags=re.S | re.I), store

def _collapse_spaces(text):
    """Схлопнуть пробелы и табы вне строковых литералов; внутри кавычек всё значимо."""
    out, i, quote = [], 0, None
    while i < len(text):
        ch = text[i]
        if quote:
            out.append(ch)
            if ch == quote: quote = None
            i += 1; continue
        if ch in '"\'':
            quote = ch; out.append(ch); i += 1; continue
        if ch in ' \t':
            while i < len(text) and text[i] in ' \t': i += 1
            out.append(' '); continue
        out.append(ch); i += 1
    return ''.join(out)

def _strip_raw_lines(block):
    """Внутри script/style/pre/textarea убираем только отступы по краям строк, не трогая пробелы внутри."""
    return '\n'.join(ln.strip() for ln in block.split('\n'))

def normalize(html):
    html = html.replace('\r\n', '\n').replace('\r', '\n')
    html = re.sub(r'<!--.*?-->', '', html, flags=re.S)
    html = re.sub(r'<meta\s+name=["\'](?:generator|generated|date)["\'][^>]*>', '', html, flags=re.I)
    # элементы с data-volatile: тег с этим атрибутом и всё содержимое до закрывающего тега того же имени (без вложенных одноимённых)
    html = re.sub(r'<(\w+)\b[^>]*\bdata-volatile\b[^>]*>.*?</\1>', '', html, flags=re.S)
    html = re.sub(r'<(\w+)\b[^>]*\bdata-volatile\b[^>]*/>', '', html)
    html, raw = _protect_raw(html)
    html = _collapse_spaces(html)
    lines = [ln.strip() for ln in html.split('\n')]
    text = '\n'.join(ln for ln in lines if ln)
    text = re.sub(r'>[ \t]*\n[ \t]*<', '><', text)
    return re.sub(r'\x00(\d+)\x00', lambda m: _strip_raw_lines(raw[int(m.group(1))]), text)

def digest(text): return hashlib.sha256(text.encode('utf-8')).hexdigest()

def main():
    ap = argparse.ArgumentParser(description="Сравнение HTML после нормализации")
    ap.add_argument('a'); ap.add_argument('b'); ap.add_argument('--show-diff', action='store_true')
    x = ap.parse_args()
    try:
        ta = open(x.a, encoding='utf-8').read(); tb = open(x.b, encoding='utf-8').read()
    except (OSError, UnicodeError) as e:
        print(f"Ошибка: не прочитан файл ({x.a} / {x.b}): {e}", file=sys.stderr); return 2
    na, nb = normalize(ta), normalize(tb)
    if na == nb:
        print(f"РАВНЫ после нормализации (sha256 {digest(na)[:16]}). Сырые файлы {'совпадают' if ta == tb else 'отличаются только шумом'}.")
        return 0
    print(f"РАЗЛИЧАЮТСЯ после нормализации: {digest(na)[:16]} против {digest(nb)[:16]}")
    d = list(difflib.unified_diff(na.split('\n'), nb.split('\n'), 'a', 'b', lineterm='', n=0))
    print(f"Строк в различиях: {sum(1 for l in d if l[:1] in '+-' and l[:3] not in ('+++', '---'))}")
    if x.show_diff: print('\n'.join(d[:80]))
    else: print("Покажи различия: --show-diff")
    return 1

if __name__ == '__main__':
    sys.exit(main())
