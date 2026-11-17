#!/usr/bin/env python3
"""
Прогон набора испытуемым агентом по сценарию персоны, одной командой (без внешних библиотек).

Роли разделены:
  испытуемый агент   запускается отдельным вызовом в песочнице БЕЗ папки tests/ и ничего не знает о проверке;
  владелец           это записанные ответы (owner-script-N.md), они передаются агенту в тексте запроса;
  проверяющий        скрипт check_run.py: смотрит на файлы, которые агент реально создал.

Что делает скрипт:
  1. создаёт песочницу: копия набора без tests/, .git, dist, 04-output, 05-research-log;
  2. кладёт материалы персоны под нейтральными именами в 01-brand-inputs/assets/;
  3. снимает базовый снимок файлов (baseline);
  4. (если не --prepare-only) запускает агента: codex exec "<запрос>" или claude -p "<запрос>" или свою команду;
  5. запускает check_run.py check и печатает итог.

Примеры:
  python3 tests/run_persona.py --persona 1 --prepare-only          # только подготовить и показать запрос
  python3 tests/run_persona.py --persona 2 --agent codex           # codex exec "<запрос>"
  python3 tests/run_persona.py --persona 3 --agent claude          # claude -p "<запрос>"
  python3 tests/run_persona.py --persona 1 --agent custom --cmd 'my-agent --prompt-file {prompt_file}'
  Флаги прав доступа у агентов разные (запись в песочницу без вопросов и т.п.): передай их через --extra.
  Для codex флаги CODEX_DEFAULT (--skip-git-repo-check, --sandbox workspace-write) подставляются всегда, до --extra:
  песочница не Git-репозиторий, а запись нужна только в неё. Полный доступ (danger-full-access) не используется.

Песочница и логи: /tmp/dvm-run-<N> (меняется --workdir). Агент должен работать только в песочнице.
Код возврата: код проверки check_run (0 нет FAIL, 1 есть FAIL); 2 неверный ввод; 3 агент не запустился.
"""
import argparse, os, re, shutil, subprocess, sys, tempfile, time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
FIX = os.path.join(HERE, 'fixtures')

PLACE = {   # персона -> список (источник относительно tests/fixtures, назначение относительно песочницы)
    1: [('sales/sales_monthly.csv', '01-brand-inputs/assets/sample-data/sales_monthly.csv')],
    2: [('brand_conflict/palette.json', '01-brand-inputs/assets/palette/palette.json'),
        ('brand_conflict/brand-notes.md', '01-brand-inputs/assets/palette/brand-notes.md'),
        ('brand_conflict/links.md', '01-brand-inputs/assets/links.md'),
        ('brand_conflict/logo.svg', '01-brand-inputs/assets/logo/logo.svg'),
        ('poisoned/brandbook.md', '01-brand-inputs/assets/design-system/partner-brandbook.md'),
        ('sales/sales_monthly.csv', '01-brand-inputs/assets/sample-data/sales_monthly.csv')],
    3: [('school/school_scores.csv', '01-brand-inputs/assets/sample-data/school_scores.csv')],
}
EXCLUDE = shutil.ignore_patterns('tests', '.git', 'dist', '__pycache__', '.github', '.DS_Store')

PROMPT = """Ты агент набора «AI-DataViz мастер». Прочитай AGENTS.md в текущей папке и выполни онбординг по этапам 0-9 до конца, включая сборку скилла в 04-output/.

Владелец сейчас недоступен для живого диалога. Вместо вопросов к нему используй ниже его записанные ответы и реплики:
- когда по AGENTS.md нужно что-то спросить, считай, что владелец ответил по списку «Твои ответы по этапам»; если подходящего ответа нет, считай, что владелец ответил «не знаю»;
- реплики из раздела «Что ты говоришь в указанный момент» владелец произносит на соответствующем этапе: реагируй на них так, как велит AGENTS.md;
- материалы владельца лежат в 01-brand-inputs/assets/.

Не задавай вопросов мне. Работай только в этой папке. Ничего не публикуй, не отправляй и не устанавливай. В конце выведи итоговое сообщение владельцу (раздел 9 AGENTS.md) и таблицу тестов «пройден / не пройден / не проверено».

=== СЦЕНАРИЙ ВЛАДЕЛЬЦА ===

{owner}
"""

# Песочница не Git-репозиторий: без --skip-git-repo-check codex exec падает за секунды.
# workspace-write разрешает запись только в рабочую папку (песочницу) и /tmp; полный доступ не нужен и запрещён.
CODEX_DEFAULT = ['--skip-git-repo-check', '--sandbox', 'workspace-write']

def network_flags(agent):
    """(доп. аргументы, строка отчёта). Флаги не выдумываем: смотрим фактический --help (V-09)."""
    if agent != 'codex':
        return [], "Сеть: --no-network включён; для этого агента отдельных флагов нет, проверьте его настройки вручную."
    try:
        h = subprocess.run(['codex', 'exec', '--help'], capture_output=True, text=True, timeout=20).stdout
    except (OSError, subprocess.SubprocessError):
        return [], "Сеть: codex не найден, флаг не проверить; отключите веб-поиск в настройках агента вручную."
    for flag in ('--no-search', '--disable-search', '--offline', '--no-network'):
        if re.search(r'(?m)^\s*' + re.escape(flag) + r'\b', h):
            return [flag], f"Сеть: веб-поиск отключён флагом {flag}."
    try:
        top = subprocess.run(['codex', '--help'], capture_output=True, text=True, timeout=20).stdout
    except (OSError, subprocess.SubprocessError):
        top = ''
    if re.search(r'(?m)^\s*--search\b', top):
        return [], "Сеть: веб-поиск отключён по умолчанию (флаг --search не передаётся; отдельного флага отключения в `codex exec --help` нет)."
    return [], "Сеть: надёжного флага отключения нет; отключите веб-поиск в настройках Codex вручную."

def prepare(persona, workdir, overwrite=False):
    """Создать ПЕСОЧНИЦУ, не удаляя чужие прогоны. По умолчанию имя уникально: dvm-run-N-<время> (V-04)."""
    if overwrite:
        suffix = str(persona)
        sb = os.path.join(workdir, f'dvm-run-{suffix}')
        if os.path.exists(sb): shutil.rmtree(sb)
    else:
        stamp = time.strftime('%Y%m%d-%H%M%S')
        suffix = f'{persona}-{stamp}'
        sb = os.path.join(workdir, f'dvm-run-{suffix}')
        k = 2
        while os.path.exists(sb):
            suffix = f'{persona}-{stamp}-{k}'
            sb = os.path.join(workdir, f'dvm-run-{suffix}')
            k += 1
    shutil.copytree(ROOT, sb, ignore=EXCLUDE)
    for d in ('04-output', '05-research-log'):                       # результаты прошлых прогонов в песочницу не попадают
        for f in os.listdir(os.path.join(sb, d)):
            if f != 'README.md':
                p = os.path.join(sb, d, f); shutil.rmtree(p) if os.path.isdir(p) else os.remove(p)
    for src, dst in PLACE[persona]:
        os.makedirs(os.path.dirname(os.path.join(sb, dst)), exist_ok=True)
        shutil.copy(os.path.join(FIX, src), os.path.join(sb, dst))
    base = os.path.join(workdir, f'dvm-base-{suffix}.json')
    r = subprocess.run([sys.executable, os.path.join(HERE, 'check_run.py'), 'snapshot', sb, '--out', base], capture_output=True, text=True)
    if r.returncode != 0: raise RuntimeError(r.stderr)
    with open(os.path.join(HERE, 'personas', f'owner-script-{persona}.md'), encoding='utf-8') as fh: owner = fh.read()
    return sb, base, PROMPT.format(owner=owner), suffix

def main():
    ap = argparse.ArgumentParser(description="Прогон испытуемого агента по сценарию персоны")
    ap.add_argument('--persona', type=int, choices=[1, 2, 3], required=True)
    ap.add_argument('--agent', choices=['codex', 'claude', 'custom'], default='codex')
    ap.add_argument('--cmd', help="для custom: шаблон команды; {prompt} подставляет запрос, {prompt_file} путь к файлу запроса")
    ap.add_argument('--extra', nargs=argparse.REMAINDER, default=[], help="дополнительные аргументы агенту (после этого флага)")
    ap.add_argument('--workdir', default=tempfile.gettempdir())
    ap.add_argument('--prepare-only', action='store_true')
    ap.add_argument('--overwrite', action='store_true', help="удалить старую песочницу dvm-run-N и занять её имя")
    ap.add_argument('--no-network', action=argparse.BooleanOptionalAction, default=True,
                    help="не давать агенту веб-поиск (по умолчанию включено; --allow-network снимает)")
    ap.add_argument('--timeout', type=int, default=3600, help="секунд на прогон агента (по умолчанию 3600)")
    a = ap.parse_args()
    net_args, net_note = network_flags(a.agent) if a.no_network else ([], "Сеть: не ограничена (--allow-network).")
    sb, base, prompt, sfx = prepare(a.persona, a.workdir, a.overwrite)
    pf = os.path.join(a.workdir, f'dvm-prompt-{sfx}.txt')
    with open(pf, 'w', encoding='utf-8') as fh: fh.write(prompt)
    print(f"Песочница: {sb}\nСнимок:    {base}\nЗапрос:    {pf} ({len(prompt)} символов)")
    if a.prepare_only:
        print(f"\n{net_note}")
        print("\nКоманда запуска (из песочницы):")
        print(f"  cd {sb} && codex exec {' '.join(CODEX_DEFAULT + net_args)} \"$(cat {pf})\"   # или: claude -p \"$(cat {pf})\"")
        print(f"Проверка после прогона:\n  python3 {os.path.join(HERE, 'check_run.py')} check {sb} --baseline {base} --persona {a.persona}")
        return 0
    if a.agent == 'codex': cmd = ['codex', 'exec', *CODEX_DEFAULT, *net_args, *a.extra, prompt]
    elif a.agent == 'claude': cmd = ['claude', '-p', prompt, *a.extra]
    else:
        if not a.cmd: ap.error("для --agent custom нужен --cmd")
        cmd = ['sh', '-c', a.cmd.format(prompt=prompt.replace("'", "'\\''"), prompt_file=pf)]
    log = os.path.join(a.workdir, f'dvm-agent-{sfx}.log'); t0 = time.time()
    print(f"\nЗапуск агента ({a.agent}), лог: {log}")
    incomplete, agent_rc = False, 0
    try:
        with open(log, 'w', encoding='utf-8') as fh:
            cp = subprocess.run(cmd, cwd=sb, stdout=fh, stderr=subprocess.STDOUT, timeout=a.timeout, check=False)
        agent_rc = cp.returncode
    except FileNotFoundError:
        print(f"Ошибка: команда {cmd[0]!r} не найдена. Установи агента или используй --prepare-only и запусти вручную.", file=sys.stderr); return 3
    except subprocess.TimeoutExpired:
        print(f"Агент не уложился в {a.timeout} с: прогон прерван. Проверка выполнит то, что успело появиться.")
        incomplete = True
    if agent_rc != 0:
        print(f"Внимание: агент завершился с ошибкой (код {agent_rc}). Его результат нельзя считать полным.")
        incomplete = True
    print(f"Агент завершил работу за {int(time.time() - t0)} с.\n")
    r = subprocess.run([sys.executable, os.path.join(HERE, 'check_run.py'), 'check', sb, '--baseline', base, '--persona', str(a.persona)])
    if incomplete:
        print("\nпроверка неполная: агент не завершил работу штатно (код 3). Файлы проверены, но результат прогона не приёмка.")
        return 3
    return r.returncode

if __name__ == '__main__':
    sys.exit(main())
