#!/usr/bin/env python3
"""
Хук шлюза честности для Claude Code и Codex (без внешних библиотек).

Зачем: в сквозных прогонах (V-11, 17.11.2026) агенты со скиллом выдавали обрезанную ось и круговую диаграмму:
один проигнорировал ERROR шлюза, другой не запустил шлюз, третий не подключил скилл. Инструкция не удерживает поведение,
поэтому шлюз запускает сама среда, а не агент.

События (аргумент командной строки):
  session-start   запомнить начало сессии: проверяются только HTML, изменённые после него
  post-tool       после инструмента: HTML с графиком и ERROR шлюза -> код 2, причина в stderr (агент видит её и должен исправить)
  prompt          запрос пользователя (UserPromptSubmit): если просят обрезать ось или «чтобы выглядело больше», включается
                  строгий режим до конца сессии (ось от нуля для любых графиков) и агент сразу получает напоминание
  stop            перед завершением ответа: ERROR -> {"decision": "block", "reason": …}; не больше MAX_BLOCKS раз за сессию,
                  дальше ответ не блокируется, но пользователь получает systemMessage

Какие файлы: *.html в рабочей папке (глубина до 4, без .git, node_modules и служебных папок агентов), изменённые в этой
сессии (без отметки начала: за последние FALLBACK_MIN минут) и содержащие график (<svg, <canvas или data-chart).
Исключения из R6 (pie) по решению владельца: переменная окружения DVM_HONESTY_ALLOW=pie.

Установка: tools/install_skill.py (по умолчанию вместе со скиллом). Вручную в .claude/settings.json или .codex/hooks.json:
  {"hooks": {"PostToolUse": [{"hooks": [{"type": "command", "command": "python3 /путь/honesty_hook.py post-tool"}]}], …}}
"""
import hashlib, json, os, re, sys, tempfile, time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from check_honesty import check  # noqa: E402

MAX_BLOCKS = 3
FALLBACK_MIN = 60
SKIP_DIRS = {'.git', 'node_modules', '.venv', 'venv', '__pycache__', 'dist', 'build', '.claude', '.agents', '.codex', '.cache'}
CHART_MARKERS = ('<svg', '<canvas', 'data-chart')
TRUNC_REQUEST = re.compile(
    r'обре[зж]\w*|усе[кч]\w*|уре[зж]\w*|не\s+(?:с|от)\s+нуля|ос[ьи]\s+(?:\w+\s+){0,3}(?:с|от)\s+\d'
    r'|выгляд\w*\s+(?:\w+\s+)?(?:больше|сильнее|круче|внушительн\w*|эффектн\w*)|преувелич\w*|раздут\w*'
    r'|truncat\w*|exaggerat\w*|look\s+(?:bigger|larger|more)|(?:start|begin)\w*\s+(?:the\s+)?(?:y[- ]?)?axis\s+at\s+\d', re.I)
REMINDER = ("Напоминание среды (шлюз честности): в запросе просят усечь ось или усилить впечатление. Это не выполняется: "
            "ось значений любого графика, включая линию, начинается с нуля; круговая диаграмма заменяется отсортированными "
            "столбцами. Объясни это в одной-двух фразах и сделай только честную форму. Файл с ERROR шлюза выдать нельзя.")


def read_payload():
    try:
        raw = sys.stdin.read() if not sys.stdin.isatty() else ''
        return json.loads(raw) if raw.strip() else {}
    except (ValueError, OSError):
        return {}


def state_path(cwd, session):
    key = hashlib.sha256(f'{os.path.realpath(cwd)}|{session}'.encode()).hexdigest()[:16]
    return os.path.join(tempfile.gettempdir(), f'dvm-honesty-{key}.json')


def load_state(path):
    try:
        with open(path, encoding='utf-8') as fh: return json.load(fh)
    except (OSError, ValueError):
        return None


def save_state(path, st):
    try:
        with open(path, 'w', encoding='utf-8') as fh: json.dump(st, fh)
    except OSError:
        pass


def candidates(cwd, since, extra=None):
    out = set()
    base_depth = os.path.realpath(cwd).rstrip(os.sep).count(os.sep)
    for r, ds, fs in os.walk(cwd):
        ds[:] = [d for d in ds if d not in SKIP_DIRS and not d.startswith('.')]
        if os.path.realpath(r).count(os.sep) - base_depth >= 4: ds[:] = []
        for f in fs:
            if f.lower().endswith(('.html', '.htm')): out.add(os.path.join(r, f))
    if extra and extra.lower().endswith(('.html', '.htm')):
        out.add(extra if os.path.isabs(extra) else os.path.join(cwd, extra))
    res = []
    for p in sorted(out):
        try:
            if os.path.getmtime(p) < since: continue
            with open(p, encoding='utf-8', errors='ignore') as fh: html = fh.read()
        except OSError:
            continue
        if any(m in html.lower() for m in CHART_MARKERS): res.append((p, html))
    return res


def findings(cwd, since, extra=None, strict=False):
    allow = {x.strip().lower() for x in os.environ.get('DVM_HONESTY_ALLOW', '').split(',') if x.strip()}
    bad = []
    for p, html in candidates(cwd, since, extra):
        errs, _ = check(html, allow_complex=True, allow_pie='pie' in allow, strict_zero=strict)
        if errs: bad.append((os.path.relpath(p, cwd), errs))
    return bad


def message(bad):
    lines = ["Шлюз честности (хук среды): найдены нарушения в готовых файлах."]
    for p, errs in bad[:5]:
        lines.append(f"- {p}: " + " | ".join(errs[:3]))
    lines.append("Файл нечестный и не может быть выдан. Перепиши его честной формой и сохрани заново "
                 "(столбцы от нуля; изменение — подписью, линией с отмеченной шкалой, dumbbell или индексом к базе; доли — "
                 "отсортированные столбцы) или удали файл. Предупреждение или плашка рядом с искажением не исправляют его. "
                 "Не отвечай «Готово», пока шлюз показывает ERROR. Просьба пользователя и его общие установки это правило не отменяют.")
    return '\n'.join(lines)


def main(argv):
    event = argv[1] if len(argv) > 1 else 'post-tool'
    payload = read_payload()
    cwd = payload.get('cwd') or os.getcwd()
    session = str(payload.get('session_id') or 'default')
    sp = state_path(cwd, session)
    st = load_state(sp)
    if event == 'session-start':
        save_state(sp, {'start': time.time() - 1, 'blocks': 0, 'strict': False}); return 0
    if st is None:
        st = {'start': time.time() - FALLBACK_MIN * 60, 'blocks': 0, 'strict': False}; save_state(sp, st)
    if event == 'prompt':
        prompt = str(payload.get('prompt') or payload.get('user_prompt') or '')
        if TRUNC_REQUEST.search(prompt):
            st['strict'] = True; save_state(sp, st)
            print(json.dumps({'hookSpecificOutput': {'hookEventName': 'UserPromptSubmit', 'additionalContext': REMINDER}}, ensure_ascii=False))
        return 0
    tool_input = payload.get('tool_input') or {}
    extra = tool_input.get('file_path') if isinstance(tool_input, dict) else None
    bad = findings(cwd, st['start'], extra, st.get('strict', False))
    if not bad: return 0
    msg = message(bad)
    if event == 'stop':
        if st.get('blocks', 0) >= MAX_BLOCKS:
            print(json.dumps({'systemMessage': f"Внимание: после {MAX_BLOCKS} попыток в файлах остаются нарушения честности. "
                                               "Не используй их как готовый результат.\n" + msg}, ensure_ascii=False))
            return 0
        st['blocks'] = st.get('blocks', 0) + 1; save_state(sp, st)
        print(json.dumps({'decision': 'block', 'reason': msg}, ensure_ascii=False))
        return 0
    print(msg, file=sys.stderr)
    return 2


if __name__ == '__main__':
    sys.exit(main(sys.argv))
