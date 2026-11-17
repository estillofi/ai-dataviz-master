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

Хук шлюза честности (по умолчанию; --no-hook отключает): в <скилл>/hooks/ копируются tools/honesty_hook.py и
tools/check_honesty.py, а в настройки агента добавляются события SessionStart, UserPromptSubmit, PostToolUse и Stop:
  Claude Code  <репо>/.claude/settings.json  или  ~/.claude/settings.json
  Codex        <репо>/.codex/hooks.json      или  ~/.codex/hooks.json   (Codex запускает хуки после подтверждения доверия)
Существующие настройки сохраняются (рядом копия .bak), повторная установка хук не дублирует.
Зачем: инструкция не удерживает агента от нечестного графика (V-11); хук запускает шлюз сам и не даёт выдать файл с ERROR.
"""
import argparse, json, os, shutil, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from validate_skill import validate

def targets(name, target, scope, home, repo):
    out = []
    if target in ('claude', 'both'):
        out.append(('Claude', os.path.join(home if scope == 'user' else repo, '.claude', 'skills', name)))
    if target in ('codex', 'both'):
        out.append(('Codex', os.path.join(home if scope == 'user' else repo, '.agents', 'skills', name)))
    return out

KIT_TOOLS = os.path.dirname(os.path.abspath(__file__))
HOOK_FILES = ('honesty_hook.py', 'check_honesty.py')
HOOK_EVENTS = (('SessionStart', 'session-start', None), ('UserPromptSubmit', 'prompt', None), ('PostToolUse', 'post-tool', None), ('Stop', 'stop', None))

def hook_config_path(label, scope, home, repo):
    base = home if scope == 'user' else repo
    return os.path.join(base, '.claude', 'settings.json') if label == 'Claude' else os.path.join(base, '.codex', 'hooks.json')

def merge_hooks(cfg_path, script, dry_run=False):
    """Добавить события хука в JSON-настройки, не трогая чужие. Возвращает строку отчёта."""
    cfg = {}
    if os.path.exists(cfg_path):
        try:
            with open(cfg_path, encoding='utf-8') as fh: cfg = json.load(fh)
        except (OSError, ValueError) as e:
            return f"хук НЕ добавлен: не удалось прочитать {cfg_path} ({e}); добавь вручную, см. tools/honesty_hook.py"
        if not isinstance(cfg, dict):
            return f"хук НЕ добавлен: {cfg_path} не JSON-объект"
    hooks = cfg.setdefault('hooks', {})
    added = []
    for event, arg, matcher in HOOK_EVENTS:
        cmd = f'python3 "{script}" {arg}'
        groups = hooks.setdefault(event, [])
        if any('honesty_hook.py' in h.get('command', '') and h.get('command', '').endswith(arg)
               for g in groups if isinstance(g, dict) for h in g.get('hooks', []) if isinstance(h, dict)):
            continue
        group = {'hooks': [{'type': 'command', 'command': cmd, 'timeout': 60}]}
        if matcher: group['matcher'] = matcher
        groups.append(group); added.append(event)
    if not added: return f"хук уже есть в {cfg_path}"
    if dry_run: return f"добавил бы хук ({', '.join(added)}) в {cfg_path}"
    os.makedirs(os.path.dirname(cfg_path), exist_ok=True)
    if os.path.exists(cfg_path): shutil.copy2(cfg_path, cfg_path + '.bak')
    with open(cfg_path, 'w', encoding='utf-8') as fh: json.dump(cfg, fh, ensure_ascii=False, indent=2); fh.write('\n')
    return f"хук ({', '.join(added)}) добавлен в {cfg_path}"

def main():
    ap = argparse.ArgumentParser(description="Установка скилла для Claude Code и Codex")
    ap.add_argument('skill_dir')
    ap.add_argument('--target', choices=['claude', 'codex', 'both'], default='both')
    ap.add_argument('--scope', choices=['user', 'repo'], default='user')
    ap.add_argument('--home', default=os.path.expanduser('~'))
    ap.add_argument('--repo', default=os.getcwd())
    ap.add_argument('--force', action='store_true')
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--no-hook', action='store_true', help="не ставить хук шлюза честности")
    a = ap.parse_args()
    src = os.path.abspath(a.skill_dir)
    errors, warns = validate(src)
    for w in warns: print(f"WARN  {w}")
    if errors:
        for e in errors: print(f"ERROR {e}")
        print("\nСкилл не прошёл проверку. Установка отменена."); return 1
    name = os.path.basename(src)
    home, repo = os.path.abspath(a.home), os.path.abspath(a.repo)
    for label, dst in targets(name, a.target, a.scope, home, repo):
        if os.path.exists(dst) and not a.force:
            print(f"{label}: {dst} уже существует, пропускаю (используй --force)")
        elif a.dry_run:
            print(f"{label}: скопировал бы {src} -> {dst}")
        else:
            if os.path.exists(dst): shutil.rmtree(dst)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copytree(src, dst, ignore=shutil.ignore_patterns('.git', '__pycache__', '.DS_Store'))
            print(f"{label}: установлено в {dst}")
        if a.no_hook: continue
        script = os.path.join(dst, 'hooks', 'honesty_hook.py')
        if not a.dry_run and os.path.isdir(dst):
            os.makedirs(os.path.dirname(script), exist_ok=True)
            for f in HOOK_FILES: shutil.copy2(os.path.join(KIT_TOOLS, f), os.path.join(dst, 'hooks', f))
        print(f"{label}: " + merge_hooks(hook_config_path(label, a.scope, home, repo), script, a.dry_run))
        if label == 'Codex' and not a.dry_run:
            print("Codex: проектные хуки запускаются после подтверждения доверия; при первом запуске Codex разреши хук honesty_hook.py.")
    print(f"\nГотово. Codex: явный вызов `${name}`. Claude Code: скилл подключается по описанию. Перезапусти агента и проверь в новом чате.")
    return 0

if __name__ == '__main__':
    sys.exit(main())
