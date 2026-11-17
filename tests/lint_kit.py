#!/usr/bin/env python3
"""
Линтер набора AI-DataViz мастер (без внешних библиотек).

Проверяет целостность самого репозитория:
  1. Ссылки на файлы в Markdown (внутри `обратных кавычек` вне блоков кода и в [ссылках](...)) ведут в существующие файлы.
  2. Нет заготовок {{...}} вне 03-skill-template/ и tests/.
  3. Парные ``` в Markdown (блоки кода закрыты).
  4. Python-файлы компилируются.
  5. Нет запрещённых терминов (бренд-специфика не должна попадать в открытый репозиторий).
  6. Нет устаревшего имени AGENT.md (канонично AGENTS.md).
  7. Каждый файл стиля содержит раздел «0.» и HTML-скелет; ядро состоит из 7 файлов.
  8. AGENTS.md содержит все этапы 0-9.
  9. Пример acme-dataviz проходит validate_skill.

Запуск: python3 tests/lint_kit.py       Код возврата 0 если ошибок нет.
"""
import os, re, sys, py_compile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
SKIP_DIRS = {'.git', '__pycache__', 'dist', 'node_modules'}
GENERATED_PREFIXES = ('04-output/', '05-research-log/', '00-session/state.md', '01-brand-inputs/assets/', 'tests/reports/', 'dist/', '/tmp', '~')   # assets/: материалы владельца, в репозитории их нет
FORBIDDEN = [r'(?<![А-Яа-яЁё])Кори(?![а-яё])', r'Корифей', r'(?i)\bkoriphey\b', r'(?i)\bkori-hub\b']
SELF_EXCLUDE = {'tests/lint_kit.py', 'tests/test_tools.py'}
ROOTS = ('00-session', '01-brand-inputs', '02-references', '03-skill-template', '04-output', '05-research-log', 'tools', 'tests', 'docs')

def walk():
    for r, ds, fs in os.walk(ROOT):
        ds[:] = [d for d in ds if d not in SKIP_DIRS and not (r == ROOT and d in {'04-output', '05-research-log'})]
        for f in fs:
            p = os.path.join(r, f)
            yield p, os.path.relpath(p, ROOT).replace(os.sep, '/')

def text_files(ext):
    for p, rel in walk():
        if p.endswith(ext): yield p, rel

def main():
    errors = []
    def err(rel, msg): errors.append(f"{rel}: {msg}")
    md = list(text_files('.md'))
    for p, rel in md:
        with open(p, encoding='utf-8') as fh: t = fh.read()
        # 3. fences
        if t.count('```') % 2: err(rel, "нечётное число ``` (блок кода не закрыт)")
        stripped = re.sub(r'```.*?```', '', t, flags=re.S)
        # 1. links
        if not rel.startswith(('tests/reports/', '04-output/', '05-research-log/')):
            cands = set(re.findall(r'`([^`\n]+)`', stripped)) | set(re.findall(r'\]\(([^)#\s]+)\)', stripped))
            for c in cands:
                c = c.strip()
                if not re.match(r'^(?:\./|\.\./)?(?:' + '|'.join(ROOTS) + r')/[\w\-./]*[\w\-]\.(?:md|py|html|css|csv|json|svg|txt|yml)$|^(?:AGENTS|CLAUDE|README|CONTRIBUTING|CHANGELOG|NOTICE|LICENSE)(?:\.md)?$|^(?:\./|\.\./)(?:[\w\-]+/)*[\w\-]+\.(?:md|py|html)$', c):
                    continue
                if any(ch in c for ch in '<>*{}…') or c.startswith(GENERATED_PREFIXES) or re.search(r'-N[.-]|persona-N', c): continue   # шаблоны имён вида owner-script-N.md
                if c.startswith('http') or c == 'LICENSE': continue
                base = os.path.dirname(p)
                if not (os.path.exists(os.path.join(ROOT, c)) or os.path.exists(os.path.normpath(os.path.join(base, c)))):
                    # пути внутри скиллов (references/…, assets/…) относятся к самому скиллу, а не к корню репозитория
                    if re.match(r'^(references|assets|examples|evals|scripts)/', c): continue
                    err(rel, f"ссылка на несуществующий файл: {c}")
        # 2. placeholders
        if '{{' in t and not rel.startswith(('03-skill-template/', 'tests/', 'docs/', 'README.md', '02-references/styles/')):
            if not rel.startswith('02-references/examples/acme-dataviz/') or '{{' in t:
                err(rel, "остались заготовки {{...}}")
        # 6. old name
        if re.search(r'\bAGENT\.md\b', t) and rel not in SELF_EXCLUDE: err(rel, "устаревшее имя AGENT.md (канонично AGENTS.md)")
    # 5. forbidden terms
    for p, rel in walk():
        if rel in SELF_EXCLUDE or not rel.endswith(('.md', '.py', '.html', '.css', '.json', '.txt', '.yml', '.svg', '.csv')): continue
        with open(p, encoding='utf-8', errors='ignore') as fh: t = fh.read()
        for pat in FORBIDDEN:
            m = re.search(pat, t)
            if m: err(rel, f"запрещённый термин (бренд-специфика): {m.group(0)!r}")
    # 4. python compile
    for p, rel in text_files('.py'):
        try: py_compile.compile(p, doraise=True)
        except py_compile.PyCompileError as e: err(rel, f"не компилируется: {e.msg}")
    # 7. styles and core
    for s in ('yau', 'fragapane', 'bremer', 'lupi', 'nyt'):
        p = os.path.join(ROOT, '02-references', 'styles', f'{s}.md')
        if not os.path.exists(p): err(f'02-references/styles/{s}.md', "нет файла стиля"); continue
        with open(p, encoding='utf-8') as fh: t = fh.read()
        if '## 0.' not in t: err(f'styles/{s}.md', "нет раздела «0.»")
        if '<!DOCTYPE html>' not in t: err(f'styles/{s}.md', "нет HTML-скелета")
    core = [f for f in os.listdir(os.path.join(ROOT, '02-references', 'core-rules')) if f.endswith('.md')]
    if len(core) != 7: err('02-references/core-rules', f"ожидалось 7 файлов ядра, найдено {len(core)}")
    # 8. stages
    with open(os.path.join(ROOT, 'AGENTS.md'), encoding='utf-8') as fh: a = fh.read()
    for i in range(10):
        if not re.search(rf'^### Этап {i}\.', a, re.M): err('AGENTS.md', f"нет заголовка «Этап {i}.»")
    # 9. example skill
    from validate_skill import validate
    ex = os.path.join(ROOT, '02-references', 'examples', 'acme-dataviz')
    e, _ = validate(ex)
    for x in e: err('02-references/examples/acme-dataviz', x)
    for e in errors: print("ERROR", e)
    print(f"\nlint: ошибок {len(errors)}")
    return 1 if errors else 0

if __name__ == '__main__':
    sys.exit(main())
