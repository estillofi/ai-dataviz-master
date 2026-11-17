#!/usr/bin/env python3
"""
Предполётная проверка снимка набора (без внешних библиотек). Запускай ПЕРВЫМ делом, до любых тестов.

Отвечает на вопрос «у меня тот самый, целый снимок?»:
  1. читается VERSION и сравнивается с ожидаемой (--expect, по умолчанию версия из VERSION самого задания тестировщику);
  2. на месте все обязательные файлы (инструменты, харнес, сценарии владельцев, ядро, шаблоны);
  3. файлы совпадают с MANIFEST.sha256 (нет изменённых, отсутствующих, лишних).

Код возврата: 0 снимок целый; 1 снимок не тот или неполный (не продолжай тестирование, получи правильный архив); 2 ошибка запуска.
Запуск из корня набора:  python3 tests/preflight.py [--expect 0.1.0-rc3] [--no-manifest]
"""
import argparse, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'tools'))

REQUIRED = [
    'VERSION', 'MANIFEST.sha256', 'AGENTS.md', 'CLAUDE.md', 'README.md', 'LICENSE',
    'tools/palette_audit.py', 'tools/validate_skill.py', 'tools/install_skill.py', 'tools/bundle_single_file.py',
    'tools/check_tokens.py', 'tools/check_honesty.py', 'tools/compare_outputs.py', 'tools/suppress_small_groups.py', 'tools/make_manifest.py',
    'tests/lint_kit.py', 'tests/run_persona.py', 'tests/check_run.py', 'tests/preflight.py', 'tests/CODEX-TESTER-TASK.md',
    'tests/personas/build_owner_scripts.py', 'tests/personas/owner-script-1.md', 'tests/personas/owner-script-2.md', 'tests/personas/owner-script-3.md',
    'tests/personas/persona-1-novice.md', 'tests/personas/persona-2-brand-conflict.md', 'tests/personas/persona-3-school-pii.md',
    'tests/fixtures/sales/sales_monthly.csv', 'tests/fixtures/school/school_scores.csv', 'tests/fixtures/poisoned/brandbook.md',
    'tests/fixtures/brand_conflict/palette.json', 'tests/fixtures/fake_agents/good_agent.py', 'tests/fixtures/fake_agents/bad_agent.py',
    '02-references/core-rules/01-integrity-and-perception.md', '02-references/core-rules/06-data-handling-and-ethics.md',
    '03-skill-template/SKILL.template.md', '03-skill-template/assets/dashboard-skeleton.html',
    '02-references/examples/acme-dataviz/SKILL.md',
]

def expected_from_task():
    """Версия, которую ожидает файл задания тестировщику (строка «Ожидаемая версия набора: X»)."""
    p = os.path.join(ROOT, 'tests', 'CODEX-TESTER-TASK.md')
    if not os.path.isfile(p): return None
    with open(p, encoding='utf-8') as fh: m = re.search(r'Ожидаемая версия набора:\s*`?([\w.\-]+)`?', fh.read())
    return m.group(1) if m else None

def main():
    ap = argparse.ArgumentParser(description="Предполётная проверка снимка набора")
    ap.add_argument('--expect', help="ожидаемая версия (по умолчанию из файла задания тестировщику)")
    ap.add_argument('--no-manifest', action='store_true', help="не сверять с MANIFEST.sha256")
    a = ap.parse_args()
    problems = []
    vp = os.path.join(ROOT, 'VERSION')
    version = open(vp, encoding='utf-8').read().strip() if os.path.isfile(vp) else None
    expect = a.expect or expected_from_task()
    print(f"Версия снимка:  {version or 'НЕ НАЙДЕНА'}")
    print(f"Ожидаемая:      {expect or 'не задана'}")
    if version is None: problems.append("нет файла VERSION: это старая версия набора (до rc3) или неполная копия")
    elif expect and version != expect: problems.append(f"версия {version}, а ожидается {expect}")
    missing = [p for p in REQUIRED if not os.path.isfile(os.path.join(ROOT, p))]
    print(f"Обязательные файлы: {'все на месте' if not missing else 'ОТСУТСТВУЮТ ' + str(len(missing))}")
    if missing:
        for p in missing[:15]: print(f"   нет: {p}")
        problems.append(f"отсутствуют обязательные файлы ({len(missing)}), например {missing[0]}")
    if not a.no_manifest and os.path.isfile(os.path.join(ROOT, 'MANIFEST.sha256')):
        from make_manifest import compare
        changed, mis, extra = compare()
        print(f"Манифест: изменены {len(changed)}, отсутствуют {len(mis)}, лишние {len(extra)}")
        for lab, items in (('изменён', changed), ('отсутствует', mis), ('лишний', extra)):
            for i in items[:8]: print(f"   {lab}: {i}")
        if changed or mis: problems.append("файлы не совпадают с манифестом: снимок изменён или повреждён")
        if extra and not (changed or mis): print("   (лишние файлы допустимы, если это ваши отчёты или материалы; проверь, что это не подмена)")
    elif not a.no_manifest:
        problems.append("нет MANIFEST.sha256: снимок собран не по правилам или неполный")
    print()
    if problems:
        print("ВЕРДИКТ: СНИМОК НЕ ТОТ ИЛИ НЕПОЛНЫЙ")
        for p in problems: print(f"  - {p}")
        print("\nЧто делать: НЕ продолжай тестирование и НЕ имитируй недостающее. Возьми правильный архив нужной версии,"
              "\nраспакуй его в чистую папку и запусти проверку заново из неё. В отчёте укажи вывод этой команды.")
        return 1
    print("ВЕРДИКТ: снимок целый, можно тестировать")
    return 0

if __name__ == '__main__':
    sys.exit(main())
