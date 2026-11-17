#!/usr/bin/env python3
"""
Собирает ОДИН файл для обычного чата без доступа к файлам (режим «только чат»).

Что внутри всегда: README, инструкция агенту (AGENTS.md), ядро правил (7 файлов), индекс стилей, плейбук ресёрча,
материалы для бренда и анкета, шаблон состояния сессии, шаблоны скилла, скелет дашборда.
Файлы стилей: по умолчанию два рекомендованных (yau, nyt). Остальные добавь через --styles (all = все пять).
Чем больше стилей, тем длиннее документ. В предисловии документа перечислено, каких файлов в нём НЕТ.

Запуск:
  python3 tools/bundle_single_file.py                          # yau + nyt -> dist/single-file-prompt.md
  python3 tools/bundle_single_file.py --styles all             # все пять стилей (длиннее)
  python3 tools/bundle_single_file.py --styles yau             # один стиль
  python3 tools/bundle_single_file.py --styles none            # без файлов стилей, только индекс
  python3 tools/bundle_single_file.py --out my-prompt.md
Затем вставь файл (или прикрепи) в чат и напиши: «Выполни этот документ. Начни с этапа 0».
"""
import argparse, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STYLES = ['yau', 'fragapane', 'bremer', 'lupi', 'nyt']
DEFAULT_STYLES = ['yau', 'nyt']

PREFACE = """# AI-DataViz мастер: единый документ для чата

**Режим «только чат».** У тебя нет доступа к файловой системе владельца. Всё, что нужно, ниже под заголовками `=== FILE: путь ===`.
Когда в инструкции написано «прочитай файл X» или «сохрани в Y»:
- файл X ищи ниже в этом документе;
- Y отдавай владельцу отдельным блоком кода с точным именем и путём, владелец сохранит сам;
- проверки, которые требуют запуска кода или браузера, помечай «не проверено», а скрипты из `tools/` предлагай владельцу запустить у себя и прислать вывод;
- состояние сессии (то, что должно лежать в `00-session/state.md`) выводи в конце каждого этапа короткой сводкой.

**Чего в этом документе нет** (не делай вид, что оно у тебя есть, скажи об этом владельцу прямо):
__MISSING__
Если владелец выберет стиль, файла которого нет, попроси его прикрепить файл из `02-references/styles/` и продолжай, когда он придёт.

Следуй `AGENTS.md` с этапа 0. Помни про приоритет: честность данных выше доступности, выше читаемости, выше бренда, выше украшений.

"""

def add(parts, rel):
    p = os.path.join(ROOT, rel)
    parts.append(f"\n\n=== FILE: {rel} ===\n\n" + open(p, encoding='utf-8').read().rstrip() + "\n")

def parse_styles(value):
    v = value.strip().lower()
    if v in ('none', 'нет'): return []
    if v == 'all': return list(STYLES)
    chosen = [x.strip() for x in v.split(',') if x.strip()]
    bad = [x for x in chosen if x not in STYLES]
    if bad: raise ValueError(f"неизвестные стили: {bad}. Допустимо: {STYLES}, all, none")
    return chosen

def main():
    ap = argparse.ArgumentParser(description="Сборка одного файла для чата")
    ap.add_argument('--styles', default=','.join(DEFAULT_STYLES), help='через запятую: yau,fragapane,bremer,lupi,nyt; all; none (по умолчанию yau,nyt)')
    ap.add_argument('--out', default=os.path.join(ROOT, 'dist', 'single-file-prompt.md'))
    a = ap.parse_args()
    try: chosen = parse_styles(a.styles)
    except ValueError as e: ap.error(str(e))
    missing = [s for s in STYLES if s not in chosen]
    missing_lines = ["- файлов шрифтов и их лицензий в бинарном виде: применяй системный запасной стек, пока владелец не приложит файлы;", "- скриптов `tools/` (ты их не запустишь);", "- примеров и тестовых данных из `tests/`, `02-references/examples/`;",
                     "- папки результатов `04-output/` (отдавай файлы блоками кода)."]
    if missing: missing_lines.insert(0, "- файлов стилей: " + ", ".join(f"`{s}`" for s in missing) + " (есть только индекс `styles/README.md`);")
    parts = [PREFACE.replace('__MISSING__', '\n'.join(missing_lines))]
    for rel in ['README.md', 'AGENTS.md']: add(parts, rel)
    for f in sorted(os.listdir(os.path.join(ROOT, '02-references', 'core-rules'))):
        if f.endswith('.md'): add(parts, f'02-references/core-rules/{f}')
    add(parts, '02-references/fonts/README.md')
    add(parts, '02-references/styles/README.md')
    for s in chosen: add(parts, f'02-references/styles/{s}.md')
    add(parts, '02-references/research-playbook.md')
    add(parts, '00-session/state.template.md')
    add(parts, '01-brand-inputs/README.md')
    add(parts, '01-brand-inputs/intake-form.md')
    add(parts, '03-skill-template/README.md')
    add(parts, '03-skill-template/SKILL.template.md')
    for f in sorted(os.listdir(os.path.join(ROOT, '03-skill-template', 'references'))): add(parts, f'03-skill-template/references/{f}')
    add(parts, '03-skill-template/evals.template.md')
    add(parts, '03-skill-template/assets/tokens.template.css')
    add(parts, '03-skill-template/assets/dashboard-skeleton.html')
    text = ''.join(parts)
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    with open(a.out, 'w', encoding='utf-8') as fh: fh.write(text)
    print(f"Готово: {a.out}\nРазмер: {len(text)//1000} тыс. символов (≈ {len(text)//3500}-{len(text)//2500} тыс. токенов: оценка, зависит от токенизатора; для кириллицы ближе к верхней границе)\nСтили: {', '.join(chosen) or 'не включены'}")

if __name__ == '__main__':
    main()
