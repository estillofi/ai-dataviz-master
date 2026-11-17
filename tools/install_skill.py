#!/usr/bin/env python3
"""
Копирует собранный скилл в папки, откуда его читают агенты (без внешних библиотек).

Папки:
  Claude (Claude Code)  пользовательская  ~/.claude/skills/<имя>   проектная  <репо>/.claude/skills/<имя>
  Codex                 пользовательская  ~/.agents/skills/<имя>   проектная  <репо>/.agents/skills/<имя>

Примеры:
  python3 tools/install_skill.py 04-output/acme-dataviz                    # и Claude, и Codex, для пользователя
  python3 tools/install_skill.py 04-output/acme-dataviz --target codex --scope repo --repo ~/work/project
  python3 tools/install_skill.py 04-output/acme-dataviz --dry-run           # только показать, что будет сделано
  python3 tools/install_skill.py 04-output/acme-dataviz --home /tmp/fake    # проверка без вреда для настоящей папки

В приложении Claude (веб, десктоп, Cowork) скилл ставится загрузкой .skill-файла в настройках, а не этим скриптом.
Перед копированием скилл проверяется validate_skill.py. Существующая папка не перезаписывается без --force.
"""
import argparse, os, shutil, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from validate_skill import validate

def targets(name, target, scope, home, repo):
    out = []
    if target in ('claude', 'both'):
        out.append(('Claude', os.path.join(home if scope == 'user' else repo, '.claude', 'skills', name)))
    if target in ('codex', 'both'):
        out.append(('Codex', os.path.join(home if scope == 'user' else repo, '.agents', 'skills', name)))
    return out

def main():
    ap = argparse.ArgumentParser(description="Установка скилла для Claude Code и Codex")
    ap.add_argument('skill_dir')
    ap.add_argument('--target', choices=['claude', 'codex', 'both'], default='both')
    ap.add_argument('--scope', choices=['user', 'repo'], default='user')
    ap.add_argument('--home', default=os.path.expanduser('~'))
    ap.add_argument('--repo', default=os.getcwd())
    ap.add_argument('--force', action='store_true')
    ap.add_argument('--dry-run', action='store_true')
    a = ap.parse_args()
    src = os.path.abspath(a.skill_dir)
    errors, warns = validate(src)
    for w in warns: print(f"WARN  {w}")
    if errors:
        for e in errors: print(f"ERROR {e}")
        print("\nСкилл не прошёл проверку. Установка отменена."); return 1
    name = os.path.basename(src)
    for label, dst in targets(name, a.target, a.scope, os.path.abspath(a.home), os.path.abspath(a.repo)):
        if os.path.exists(dst) and not a.force:
            print(f"{label}: {dst} уже существует, пропускаю (используй --force)"); continue
        if a.dry_run:
            print(f"{label}: скопировал бы {src} -> {dst}"); continue
        if os.path.exists(dst): shutil.rmtree(dst)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copytree(src, dst, ignore=shutil.ignore_patterns('.git', '__pycache__', '.DS_Store'))
        print(f"{label}: установлено в {dst}")
    print(f"\nГотово. Codex: явный вызов `${name}`. Claude Code: скилл подключается по описанию. Перезапусти агента и проверь в новом чате.")
    return 0

if __name__ == '__main__':
    sys.exit(main())
