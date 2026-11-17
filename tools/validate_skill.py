#!/usr/bin/env python3
"""
Проверка скилла по открытому формату Agent Skills (без внешних библиотек).

Что проверяет:
  ERROR  нет SKILL.md; нет frontmatter; нет name или description;
         name не из строчных латинских букв, цифр и дефисов, длиннее 64 символов или не равен имени папки;
         description пустое, длиннее 1024 символов, не взято в кавычки при наличии ': ';
         ссылки на файлы внутри скилла (references/, assets/, examples/, evals/, scripts/) ведут в никуда;
         остались заготовки {{...}}.
  WARN   в SKILL.md больше 500 строк; в описании нет слов про презентации или слайды;
         description не упоминает «график» или «chart»;
         нет эталонов: папки examples/ нет или в ней нет ни одного .html/.svg/.png;
         assets/dashboard-skeleton.html есть, но похож на заглушку (меньше 3000 байт или без <script>);
         нет папки evals/.

Режим --strict превращает предупреждения в ошибки (для приёмки перед выдачей).
ВАЖНО: валидатор проверяет структуру и наличие файлов, а не качество содержимого. Качество подтверждают
тестовая галерея, тесты скилла и одобрение владельца.

Запуск:  python3 tools/validate_skill.py [--strict] <папка-скилла>
Код возврата: 0 если ошибок нет, 1 если есть.
"""
import os, re, sys

NAME_RE = re.compile(r'^[a-z0-9]+(?:-[a-z0-9]+)*$')

def parse_frontmatter(text):
    m = re.match(r'^---\r?\n(.*?)\r?\n---\r?\n', text, re.S)
    if not m:
        return None, text, ["нет frontmatter (блок --- ... --- в начале SKILL.md)"]
    raw, body, errs, data = m.group(1), text[m.end():], [], {}
    for line in raw.splitlines():
        if not line.strip() or line.lstrip().startswith('#'):
            continue
        km = re.match(r'^([A-Za-z_][\w-]*):\s*(.*)$', line)
        if not km:
            errs.append(f"строка frontmatter не разобрана: {line[:60]!r}")
            continue
        key, val = km.group(1), km.group(2).strip()
        if val.startswith('"'):
            if not val.endswith('"') or len(val) < 2:
                errs.append(f"{key}: незакрытые двойные кавычки")
                continue
            val = val[1:-1].replace('\\"', '"').replace('\\\\', '\\')
        elif val.startswith("'"):
            if not val.endswith("'") or len(val) < 2:
                errs.append(f"{key}: незакрытые одинарные кавычки")
                continue
            val = val[1:-1].replace("''", "'")
        elif ': ' in val or val.endswith(':') or ' #' in val:
            errs.append(f"{key}: значение содержит ': ' или ' #' и не взято в кавычки (ломает YAML). Оберни в двойные кавычки")
        data[key] = val
    return data, body, errs

def validate(path):
    errors, warns = [], []
    path = os.path.abspath(path)
    skill_md = os.path.join(path, 'SKILL.md')
    if not os.path.isfile(skill_md):
        return [f"нет файла {skill_md}"], []
    with open(skill_md, encoding='utf-8') as fh:
        text = fh.read()
    data, body, ferrs = parse_frontmatter(text)
    errors += ferrs
    if data is not None:
        name, desc = data.get('name', ''), data.get('description', '')
        if not name: errors.append("нет поля name")
        else:
            if not NAME_RE.match(name): errors.append(f"name {name!r}: допустимы строчные латинские буквы, цифры и дефисы")
            if len(name) > 64: errors.append(f"name длиннее 64 символов ({len(name)})")
            if name != os.path.basename(path): errors.append(f"name {name!r} не равен имени папки {os.path.basename(path)!r}")
        if not desc: errors.append("нет поля description")
        else:
            if len(desc) > 1024: errors.append(f"description длиннее 1024 символов ({len(desc)})")
            low = desc.lower()
            if not any(w in low for w in ('презентац', 'слайд', 'slide', 'deck')):
                warns.append("в description нет слов про презентации или слайды: скилл может не подключаться при запросах на слайды")
            if not any(w in low for w in ('график', 'chart', 'дашборд', 'dashboard')):
                warns.append("в description нет слов «график», «дашборд», chart или dashboard")
    if len(text.splitlines()) > 500:
        warns.append(f"SKILL.md длиннее 500 строк ({len(text.splitlines())}): вынеси детали в references/")
    if '{{' in text:
        errors.append("в SKILL.md остались заготовки {{...}}")
    # ссылки на файлы внутри скилла
    stripped = re.sub(r'```.*?```', '', text, flags=re.S)
    for ref in sorted(set(re.findall(r'`((?:references|assets|examples|evals|scripts)/[^`\s]+)`', stripped))):
        if any(c in ref for c in '*<>{}…') or ref.endswith('/') and not os.path.isdir(os.path.join(path, ref)):
            if ref.endswith('/') and not os.path.isdir(os.path.join(path, ref)):
                errors.append(f"папка из ссылки не найдена: {ref}")
            continue
        if not os.path.exists(os.path.join(path, ref.rstrip('/'))):
            errors.append(f"файл из ссылки не найден: {ref}")
    # эталоны, скелет, тесты (проверка заглушек)
    ex = os.path.join(path, 'examples')
    has_example = os.path.isdir(ex) and any(f.lower().endswith(('.html', '.svg', '.png')) for _, _, fs in os.walk(ex) for f in fs)
    if not has_example:
        warns.append("нет эталонов: папка examples/ отсутствует или пуста. Без эталонов предсказуемость не обеспечена")
    sk = os.path.join(path, 'assets', 'dashboard-skeleton.html')
    if os.path.isfile(sk):
        with open(sk, encoding='utf-8', errors='ignore') as fh: sk_text = fh.read()
        if os.path.getsize(sk) < 3000 or '<script' not in sk_text:
            warns.append("assets/dashboard-skeleton.html похож на заглушку (меньше 3000 байт или без <script>)")
    # шлюз честности должен лежать в самом скилле: на него ссылается раздел 0 (V-11)
    gates = [os.path.relpath(os.path.join(r, f), path) for r, _, fs in os.walk(path) for f in fs if f == 'check_honesty.py']
    if not gates:
        warns.append("нет шлюза честности: скопируй tools/check_honesty.py набора в tools/ скилла")
    for ref in sorted(set(re.findall(r'((?:[\w.-]+/)*check_honesty\.py)', stripped))):
        if not os.path.isfile(os.path.join(path, ref)):
            errors.append(f"файл из ссылки не найден: {ref} (шлюз честности, на него ссылается SKILL.md)")
    if not os.path.isdir(os.path.join(path, 'evals')):
        warns.append("нет папки evals/: у скилла нет тестов")
    # заготовки в остальных md/css
    for root, _, files in os.walk(path):
        for f in files:
            if f.endswith(('.md', '.css', '.html')) and f != 'SKILL.md':
                p = os.path.join(root, f)
                with open(p, encoding='utf-8', errors='ignore') as fh:
                    has = '{{' in fh.read()
                if has:
                    errors.append(f"остались заготовки {{...}} в {os.path.relpath(p, path)}")
    return errors, warns

def main():
    args = [a for a in sys.argv[1:] if a != '--strict']
    strict = '--strict' in sys.argv[1:]
    if len(args) != 1 or args[0] in ('-h', '--help'):
        print(__doc__); return 0 if args and args[0] in ('-h', '--help') else 2
    try:
        errors, warns = validate(args[0])
    except (OSError, UnicodeError) as e:
        print(f"Ошибка: не прочитан SKILL.md в {os.path.dirname(args[0]) or args[0]}: {e}", file=sys.stderr); return 2
    for w in warns: print(f"WARN  {w}")
    for e in errors: print(f"ERROR {e}")
    if strict and warns:
        print(f"\nСТРОГИЙ РЕЖИМ: предупреждений {len(warns)} считаются ошибками")
    print(f"\nИтого: ошибок {len(errors)}, предупреждений {len(warns)}")
    return 1 if errors or (strict and warns) else 0

if __name__ == '__main__':
    sys.exit(main())
