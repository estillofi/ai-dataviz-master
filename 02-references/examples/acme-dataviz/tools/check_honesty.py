#!/usr/bin/env python3
"""
Шлюз честности: проверка ГОТОВОГО HTML перед выдачей (без внешних библиотек).

Зачем: текстовый запрет в инструкции агент может нарушить (подтверждено внешним тестированием: агент прочитал запрет,
но выдал усечённые столбцы и круговую диаграмму «с предупреждением»). Шлюз смотрит на результат, а не на намерения.

Что ловит (ERROR: почти наверняка нарушение; результат выдавать нельзя):
  pie/donut     секторы SVG (путь из центра: M c L … A … Z), conic-gradient, кольца через stroke-dasharray,
                объявленный тип data-chart="pie|donut", слова «круговая диаграмма», pie chart, donut в подписях
  3D            perspective(), rotateX/rotateY, translateZ, preserve-3d, data-chart="3d"
  dual axis     data-dual-axis="true", объявленная вторая ось
  admitted      текст на странице признаёт искажение: «ось обрезана», «усечённая ось», «рост выглядит сильнее»,
                «визуально преувеличивает», truncated axis — на любом графике, включая линию (V-11: предупреждение не оправдывает)
  truncated     столбцы, у которых ось значений начинается не с нуля: объявлено data-axis-min ≠ 0 у типа bar/column/histogram/area,
                либо в SVG со столбцами деления оси образуют ряд без нуля (например 5, 6, 7 млн)
Предупреждения (WARN: проверь глазами):
  нет объявления типа графика (data-chart), сложная форма без разрешения, тени на данных, нет источника, нет заголовка.

Объявление типа (рекомендуется, скелеты набора его содержат):
  <svg data-chart="bar" data-axis-min="0"> …   типы: line, bar, column, dot, slope, scatter, histogram, area, stacked100,
  kpi, sparkline, table, map, small-multiples; сложные: chord, sankey, network, radial, unit (нужно --allow-complex).

ВАЖНО: это эвристика. ERROR означает «почти наверняка нарушение». Отсутствие ошибок НЕ доказывает честность графика:
тест из 10 вопросов (core/01-integrity-and-perception.md) всё равно обязателен.

Запуск:  python3 tools/check_honesty.py результат.html [ещё.html …] [--allow-complex] [--allow-pie]
         --allow-pie только если исключение R6 записано владельцем в house-style.md.
Код возврата: 0 нет ERROR; 1 есть ERROR; 2 неверный ввод.
"""
import argparse, re, sys

FORBIDDEN_TYPES = {'pie', 'donut', 'doughnut', '3d', 'radar', 'gauge', 'dual-axis'}
ZERO_BASED = {'bar', 'column', 'histogram', 'area', 'stacked100'}
COMPLEX = {'chord', 'sankey', 'alluvial', 'network', 'radial', 'unit', 'treemap', 'sunburst'}
NUM = r'[-−]?\d{1,3}(?:[ \u00a0\u202f]\d{3})+(?:[.,]\d+)?|[-−]?\d+(?:[.,]\d+)?'

def attr(tag, name):
    m = re.search(r'\b' + re.escape(name) + r'\s*=\s*("([^"]*)"|\'([^\']*)\')', tag)
    return (m.group(2) if m.group(2) is not None else m.group(3)) if m else None

def to_num(s):
    s = s.replace('−', '-').replace('\u00a0', '').replace('\u202f', '').replace(' ', '').replace(',', '.')
    try: return float(s)
    except ValueError: return None

def arithmetic_run(vals):
    """Есть ли среди чисел арифметическая прогрессия из >= 3 членов (деления оси). Возвращает её или None."""
    v = sorted(set(round(x, 6) for x in vals))
    best = None
    for i in range(len(v)):
        for j in range(i + 1, len(v)):
            step = v[j] - v[i]
            if step <= 0: continue
            run = [v[i], v[j]]
            while any(abs(x - (run[-1] + step)) < 1e-6 * max(1, abs(step)) for x in v): run.append(run[-1] + step)
            if len(run) >= 3 and (best is None or len(run) > len(best)): best = run
    return best

ADMITTED = re.compile(
    r'(?<!не )(?<!без )\b(?:обрезанн|усечённ|усеченн)\w*\s+ос(?:ь|и|ью)\b'
    r'|\bос(?:ь|и)\s+(?:значений\s+|столбцов\s+|y\s+)?(?:обрезан|усечен|усечён)\w*'
    r'|\btruncated\s+(?:y[- ]?)?axis\b|\baxis\s+(?:is\s+)?truncated\b'
    r'|\b(?:рост|разниц\w*|изменени\w*|падени\w*)\s+(?:визуально\s+)?выгляд\w*\s+(?:сильнее|больше|круче|внушительнее|заметнее)'
    r'|\bвизуально\s+преувеличива\w*', re.I)

def check(html, allow_complex=False, allow_pie=False):
    errors, warns = [], []
    body = re.sub(r'<!--.*?-->', '', html, flags=re.S)
    css = ' '.join(re.findall(r'<style[^>]*>(.*?)</style>', body, flags=re.S | re.I)) + ' ' + ' '.join(re.findall(r'style\s*=\s*"([^"]*)"', body))
    visible = re.sub(r'<(script|style)[^>]*>.*?</\1>', ' ', body, flags=re.S | re.I)
    text = re.sub(r'<[^>]+>', ' ', visible)

    # --- pie / donut ---
    pie = []
    if re.search(r'conic-gradient\s*\(', css, re.I): pie.append("conic-gradient в стилях")
    sectors = {}
    for d in re.findall(r'\bd\s*=\s*"([^"]+)"', visible):
        m = re.match(r'\s*M\s*([-\d.]+)[ ,]+([-\d.]+)\s*[Ll][^AaZz]*[Aa][^Zz]*[Zz]', d)
        if m: sectors.setdefault((m.group(1), m.group(2)), 0); sectors[(m.group(1), m.group(2))] += 1
    if any(n >= 2 for n in sectors.values()): pie.append(f"секторы SVG из общего центра ({max(sectors.values())} шт.)")
    rings = [t for t in re.findall(r'<circle\b[^>]*>', visible) if attr(t, 'stroke-dasharray') and (attr(t, 'fill') in ('none', 'transparent') or 'fill:none' in (attr(t, 'style') or '').replace(' ', ''))]
    if len(rings) >= 2: pie.append(f"кольцевые сегменты через stroke-dasharray ({len(rings)} шт.)")
    if re.search(r'кругов(ая|ой|ую)\s+диаграмм|секторн(ая|ой|ую)\s+диаграмм|\bpie\s*chart\b|\bdonut\b|\bdoughnut\b', text, re.I): pie.append("в подписях названа круговая диаграмма")
    if re.search(r'class\s*=\s*"[^"]*\b(pie|donut)\b', visible, re.I): pie.append("класс pie/donut в разметке")
    if re.search(r'\bid\s*=\s*"(?:[\w-]*[-_])?(pie|donut|doughnut)(?:[-_][\w-]*)?"', visible, re.I): pie.append("id pie/donut в разметке")
    # секторы, которые рисует скрипт: шаблон пути «M центр L точка-на-окружности A … Z» (V-11, 17.11: pie строился в JS и шлюз его не видел)
    scripts = ' '.join(re.findall(r'<script[^>]*>(.*?)</script>', body, flags=re.S | re.I))
    if re.search(r'M\s*\$\{\s*(\w+)\s*\}[ ,]*\$\{\s*(\w+)\s*\}\s*L[^`]*?Math\.(?:cos|sin)[^`]*?A\s*\$\{[^`]*?Z', scripts):
        pie.append("скрипт рисует секторы из центра (M центр L … A … Z)")
    if pie and not allow_pie: errors.append("pie/donut: " + "; ".join(pie) + ". Замена: отсортированные горизонтальные столбцы (R6)")
    elif pie: warns.append("pie/donut разрешён флагом --allow-pie: проверь, что исключение записано в house-style.md (≤ 3 части, подписи с процентами)")

    # --- 3D ---
    d3 = [k for k, p in (('perspective()', r'perspective\s*\('), ('rotateX/rotateY', r'rotate[XY]\s*\('), ('translateZ', r'translateZ\s*\('),
                          ('preserve-3d', r'preserve-3d'), ('rotate3d', r'rotate3d\s*\(')) if re.search(p, css + ' ' + visible, re.I)]
    if d3: errors.append("3D: " + ", ".join(d3) + " (R5, без исключений)")
    if re.search(r'(drop-shadow|box-shadow)\s*[:(]', css, re.I): warns.append("тени в стилях: убедись, что они не на данных (R5)")

    # --- declared types and axes ---
    svgs = re.findall(r'<svg\b[^>]*>.*?</svg>', visible, flags=re.S | re.I)
    undeclared = 0
    for svg in svgs:
        tag = re.match(r'<svg\b[^>]*>', svg).group(0)
        ctype = (attr(tag, 'data-chart') or '').strip().lower()
        if attr(tag, 'data-dual-axis') == 'true': errors.append("двойная ось объявлена (data-dual-axis): R4, без исключений. Замена: два графика или индексация к базе")
        if not ctype:
            if len(re.findall(r'<(?:rect|path|circle|line|polyline)\b', svg)) >= 3: undeclared += 1
        elif ctype in FORBIDDEN_TYPES:
            if not (allow_pie and ctype in ('pie', 'donut', 'doughnut')): errors.append(f"объявлен запрещённый тип графика: {ctype}")
        elif ctype in COMPLEX and not allow_complex:
            warns.append(f"сложная форма «{ctype}»: допустима только если разрешена в house-style.md и прошла шлюз сложности (--allow-complex)")
        amin = attr(tag, 'data-axis-min')
        if ctype in ZERO_BASED and amin is not None and (to_num(amin) or 0) != 0:
            errors.append(f"{ctype}: ось значений начинается с {amin}, а не с нуля (R1, без исключений). Замена: столбцы от нуля, либо линия или dumbbell для показа изменения")
        # геометрическая эвристика: столбцы + деления оси без нуля
        bars = [r for r in re.findall(r'<rect\b[^>]*>', svg)
                if (attr(r, 'fill') or '') not in ('none', 'transparent') and 'hit' not in (attr(r, 'class') or '')
                and 'shade' not in (attr(r, 'class') or '') and 'fill:transparent' not in (attr(r, 'style') or '').replace(' ', '')]
        if len(bars) >= 3 and ctype not in ('line', 'sparkline', 'kpi', 'scatter', 'dot', 'slope'):
            nums = []
            for t in re.findall(r'<text\b[^>]*>(.*?)</text>', svg, flags=re.S):
                t = re.sub(r'<[^>]+>', '', t).strip()
                m = re.match(r'^(' + NUM + r')\s*(?:[%₽$€]|тыс\.?|млн\.?|млрд\.?|k|m|b|ед\.?|шт\.?)?$', t, re.I)
                if m and to_num(m.group(1)) is not None: nums.append(to_num(m.group(1)))
            run = arithmetic_run(nums)
            if run and min(run) > 0 and 0 not in nums:
                errors.append(f"столбцы с осью не от нуля: деления оси {', '.join(('%g' % x) for x in run[:5])}… без нуля (R1, без исключений)")
    # признание искажения в тексте: «ось обрезана … рост выглядит сильнее». Отрицания («ось не обрезана») не считаются.
    has_chart = bool(svgs) or re.search(r'<canvas\b', visible, re.I)
    if has_chart:
        hits = sorted({m.group(0).strip() for m in ADMITTED.finditer(text)})
        if hits: errors.append("текст признаёт искажение графика: «" + "», «".join(hits[:3]) + "». Предупреждение не делает график честным: перерисуй честно (ось от нуля или изменение как dumbbell / индекс к базе) и убери оговорку")
    if undeclared: warns.append(f"{undeclared} график(ов) без объявления типа (data-chart): шлюз проверил их только эвристикой")
    if re.search(r'втор(ая|ой|ую)\s+ос[ьи]|правая\s+ось|second(ary)?\s+(y[- ]?)?axis|dual[- ]axis', text, re.I):
        errors.append("в подписях упомянута вторая ось: R4, без исключений")

    # --- обвязка ---
    if not re.search(r'<h1\b', visible, re.I): warns.append("нет заголовка <h1> (заголовок-вывод)")
    if not re.search(r'Источник|Source', text): warns.append("нет строки «Источник» (R15)")
    return errors, warns

def main():
    ap = argparse.ArgumentParser(description="Шлюз честности для готового HTML")
    ap.add_argument('files', nargs='+'); ap.add_argument('--allow-complex', action='store_true'); ap.add_argument('--allow-pie', action='store_true')
    a = ap.parse_args()
    total = 0
    for f in a.files:
        try:
            with open(f, encoding='utf-8') as fh: html = fh.read()
        except (OSError, UnicodeError) as e:
            print(f"Ошибка: не прочитан {f}: {e}", file=sys.stderr); return 2
        errors, warns = check(html, a.allow_complex, a.allow_pie)
        print(f"== {f}")
        for w in warns: print(f"  WARN  {w}")
        for e in errors: print(f"  ERROR {e}")
        if not errors and not warns: print("  ok")
        total += len(errors)
    print(f"\nИтого ERROR: {total}. " + ("РЕЗУЛЬТАТ ВЫДАВАТЬ НЕЛЬЗЯ: исправь и запусти снова." if total else "Нарушений не найдено (эвристика: тест из 10 вопросов всё равно обязателен)."))
    return 1 if total else 0

if __name__ == '__main__':
    sys.exit(main())
