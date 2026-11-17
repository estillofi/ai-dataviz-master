#!/usr/bin/env python3
"""
Проверка, что HTML использует только цвета и шрифты из токенов (без внешних библиотек).

Берёт все значения токенов из tokens.css (--имя: значение), собирает все цвета и семейства шрифтов,
которые встречаются в HTML (в <style> и в атрибутах), и сообщает о тех, которых нет среди токенов.

Допустимые исключения (по умолчанию): #fff, #ffffff, #000, #000000, transparent, currentColor, inherit, none.
Добавить свои: --allow "#123456" "rgba(0,0,0,.1)".

Что НЕ проверяется: размеры, отступы, форма. Для них действует шкала из core/03-color-typography-accessibility.md.

Запуск:  python3 tools/check_tokens.py страница.html assets/tokens.css
Код возврата: 0 замечаний нет; 1 есть замечания; 2 неверный ввод.
"""
import argparse, re, sys, zipfile

COLOR_RE = re.compile(r'#[0-9A-Fa-f]{8}\b|#[0-9A-Fa-f]{6}\b|#[0-9A-Fa-f]{3}\b|rgba?\([^)]*\)|hsla?\([^)]*\)')
DEFAULT_ALLOW = {'#fff', '#ffffff', '#000', '#000000', 'transparent', 'currentcolor', 'inherit', 'none'}

def norm_color(c):
    c = c.strip().lower().replace(' ', '')
    if re.fullmatch(r'#[0-9a-f]{3}', c): c = '#' + ''.join(ch * 2 for ch in c[1:])
    return c

def norm_font(f):
    return re.sub(r'\s+', ' ', f.strip().strip('"\'')).lower()

def token_values(css):
    colors, fonts, names = set(), set(), {}
    for m in re.finditer(r'(--[\w-]+)\s*:\s*([^;}]+?)\s*(?:;|\}|$)', css):
        name, val = m.group(1), m.group(2).strip()
        names[name] = val
        for c in COLOR_RE.findall(val): colors.add(norm_color(c))
        if 'font' in name:
            for part in val.split(','): fonts.add(norm_font(part))
    return colors, fonts, names

def main():
    ap = argparse.ArgumentParser(description="Проверка токенов в HTML или PPTX")
    ap.add_argument('html'); ap.add_argument('tokens_css')
    ap.add_argument('--allow', nargs='*', default=[])
    a = ap.parse_args()
    try:
        css = open(a.tokens_css, encoding='utf-8').read()
    except (OSError, UnicodeError) as e:
        print(f"Ошибка: не прочитан файл токенов {a.tokens_css}: {e}", file=sys.stderr); return 2
    colors, fonts, names = token_values(css)
    if not colors:
        print(f"Ошибка: в {a.tokens_css} не найдено ни одного цвета (ожидаются строки вида --accent: #0072B2;)", file=sys.stderr); return 2
    allow = DEFAULT_ALLOW | {norm_color(x) for x in a.allow}

    # V-12: цвета слайдов .pptx лежат в XML внутри zip
    if a.html.lower().endswith(('.pptx', '.potx')):
        try:
            with zipfile.ZipFile(a.html) as z:
                xml = '\n'.join(z.read(n).decode('utf-8', 'ignore') for n in z.namelist() if n.endswith('.xml'))
        except (OSError, zipfile.BadZipFile) as e:
            print(f"Ошибка: не прочитан {a.html}: {e}", file=sys.stderr); return 2
        found = {norm_color('#' + h) for h in re.findall(r'<a:srgbClr\s+val="([0-9A-Fa-f]{6})"', xml)}
        bad = sorted(found - colors - allow)
        for c in bad: print(f"ЦВЕТ вне токенов (pptx): {c}")
        print(f"\nИтого замечаний: {len(bad)}")
        return 1 if bad else 0

    try:
        html = open(a.html, encoding='utf-8').read()
    except (OSError, UnicodeError) as e:
        print(f"Ошибка: не прочитан {a.html}: {e}", file=sys.stderr); return 2
    # :root больше не вырезаем целиком (V-01): иначе объявленная на странице переменная скрывает цвет.
    body = re.sub(r'<!--.*?-->', '', html, flags=re.S)
    page_decls = [(m.group(1), m.group(2).strip()) for m in re.finditer(r'(--[\w-]+)\s*:\s*([^;}]+)', body)]
    page_vars = {}
    for name, val in page_decls: page_vars[name] = val

    def resolve(val, depth=0):
        """Раскрыть var(--x) через объявления страницы, затем токены (V-01)."""
        if depth > 10 or 'var(' not in val: return val
        def repl(m):
            name, fallback = m.group(1), (m.group(2) or '').strip()
            src = page_vars.get(name) or names.get(name)
            return resolve(src, depth + 1) if src is not None else fallback
        return re.sub(r'var\(\s*(--[\w-]+)\s*(?:,\s*([^)]*))?\)', repl, val)

    FONT_GENERIC = ('serif', 'sans-serif', 'monospace', 'cursive', 'system-ui')
    foreign, foreign_names = [], set()
    for name, val in page_decls:
        if name in names: continue                       # имя есть в tokens.css
        has_color = bool(COLOR_RE.search(val))
        has_font = 'font' in name.lower() or 'font-family' in val.lower() or any(g in val.lower() for g in FONT_GENERIC)
        if has_color or has_font:
            foreign_names.add(name)
            foreign.append(f"{name} = {val}" + (' (цвет)' if has_color else ' (шрифт)'))
    # объявления чужих переменных не считаем второй раз как «цвет вне токенов»
    scan = body
    for name in foreign_names:
        scan = re.sub(re.escape(name) + r'\s*:[^;}]*[;}]?', ' ', scan)
    scan = resolve(scan)
    bad_colors = sorted({norm_color(c) for c in COLOR_RE.findall(scan)} - colors - allow)
    bad_fonts = []
    for m in re.finditer(r'font-family\s*:\s*([^;}]+)', scan):
        val = resolve(m.group(1).strip())
        if val.count('"') % 2 == 1 and val.endswith('"'): val = val[:-1]      # закрывающая кавычка атрибута style="..."
        if val.count("'") % 2 == 1 and val.endswith("'"): val = val[:-1]
        for part in val.split(','):
            f = norm_font(part)
            if f and f not in fonts and f not in {'serif', 'sans-serif', 'monospace', 'cursive', 'system-ui', 'inherit'}: bad_fonts.append(f)
    # цвета, объявленные в :root самой страницы, но отсутствующие в tokens.css
    root = re.search(r':root\s*\{(.*?)\}', html, flags=re.S)
    drift = []
    if root:
        for m in re.finditer(r'(--[\w-]+)\s*:\s*([^;}]+?)\s*(?:;|$)', root.group(1)):
            if m.group(1) in names:
                for c in COLOR_RE.findall(m.group(2)):
                    if norm_color(c) not in {norm_color(x) for x in COLOR_RE.findall(names[m.group(1)])}:
                        drift.append(f"{m.group(1)}: в странице {norm_color(c)}, в tokens.css {names[m.group(1)]}")
    for f in foreign: print(f"НОВАЯ ПЕРЕМЕННАЯ вне токенов: {f}")
    for c in bad_colors: print(f"ЦВЕТ вне токенов: {c}")
    for f in sorted(set(bad_fonts)): print(f"ШРИФТ вне токенов: {f}")
    for d in drift: print(f"РАСХОЖДЕНИЕ токена: {d}")
    n = len(bad_colors) + len(set(bad_fonts)) + len(drift) + len(foreign)
    print(f"\nИтого замечаний: {n}")
    return 1 if n else 0

if __name__ == '__main__':
    sys.exit(main())
