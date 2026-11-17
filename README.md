<p align="center"><img src="docs/assets/flower.png" width="56" alt=""></p>

# AI-DataViz Master

[![CI](https://github.com/estillofi/ai-dataviz-master/actions/workflows/ci.yml/badge.svg)](https://github.com/estillofi/ai-dataviz-master/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

## What it is

An open-source kit for conjuring your own data-visualization assistant. You open a folder in an AI agent (or paste one file into a chat), answer ~10 short stages of questions about your team, brand and tasks, and get a portable **Agent Skill** (`SKILL.md`) that builds honest, on-brand charts, interactive pages and small dashboards, and styles data in presentations, consistently (tokens, golden examples, determinism checks).

## Quick start

```bash
git clone https://github.com/estillofi/ai-dataviz-master.git
cp -r ai-dataviz-master ~/dataviz-master-work && cd ~/dataviz-master-work && rm -rf .git
python3 tests/lint_kit.py          # only Python 3.9+ is needed
```

Open that folder in an agent (Claude Cowork / Claude Code / Codex CLI / any agent with file access) and say: “Read `AGENTS.md` in this folder and start the onboarding.” Full instructions: [docs/BUILD-GUIDE.md](docs/BUILD-GUIDE.md).

## How it works

The agent reads `AGENTS.md`, asks small batches of questions, audits the palette, builds a closed catalog of chart forms, copies the integrity rules, assembles `<slug>-dataviz/`, then checks the result with the tools in `tools/` (contrast, tokens, honesty gate, reproducibility, small groups, skill structure). The harness in `tests/` runs the whole flow against synthetic personas and inspects the files the agent actually wrote.

## Status

0.2.0. Verified: tooling and harness (unit tests, kit lint, preflight, browser tests for the skeletons); a full onboarding run of persona 2 with Codex (`check_run`: 0 FAIL; injected instruction ignored; pie, 3D and truncated bars refused in the house style); end-to-end refusal test V-11 (truncate the axis and draw a pie chart) **passed in Codex and Claude Code** with the installed honesty hook: both agents refused and shipped only honest charts. See `tests/reports/`.

**How honesty is enforced.** Instructions alone did not hold: without the hook, three of three runs shipped a truncated axis or a pie chart. `tools/install_skill.py` therefore installs a hook (Claude Code `.claude/settings.json`, Codex `.codex/hooks.json`) that runs the honesty gate on every chart HTML saved in the session, blocks the answer while the gate reports ERROR, and switches to a strict zero-axis mode when the user asks to exaggerate. Codex runs project hooks only after you trust them once.

**Known limits:** the gate is a static heuristic (charts rendered from external data at runtime are checked only by their markup and scripts); V-11 was verified once per agent; independent reproducibility runs, full WCAG and screen-reader checks are not done. Behaviour still depends on the agent.

## License

MIT, see [LICENSE](LICENSE) and [NOTICE.md](NOTICE.md).

---

## Что это

Набор текстовых файлов и маленьких скриптов, в котором **агент ведёт человека через онбординг** и собирает ему персональный скилл визуализации данных.

Зачем:

- Человеку без опыта в данных нужны **строгие профессиональные правила**: честные оси, без круговых и 3D, без двойных осей, с источником и выводом в заголовке.
- Команде нужен **свой визуальный язык**: палитра, шрифты, тон, шаблоны презентаций.
- Результат должен быть **предсказуемым**: один запрос, один и тот же вид.

Что получаете:

- Скилл `<название>-dataviz` с токенами бренда, закрытым каталогом простых графиков, правилами дашбордов и презентаций, ядром честности и выбранными базовыми стилями.
- Отчёт по палитре (контраст WCAG и различимость для дальтоников).
- Тестовую галерею на ваших данных и тесты скилла.

## Быстрый старт (3 минуты)

```bash
git clone https://github.com/estillofi/ai-dataviz-master.git
cp -r ai-dataviz-master ~/dataviz-master-work && cd ~/dataviz-master-work && rm -rf .git
python3 tests/lint_kit.py          # проверка, что набор цел (нужен только Python 3.9+)
```

Откройте **эту папку** в агенте (Claude Cowork / Claude Code / Codex CLI / любой агент с доступом к файлам) и скажите:

```
Прочитай AGENTS.md в этой папке и начни онбординг. Веди меня по этапам, задавай вопросы небольшими порциями.
```

Агента с файлами нет? Соберите один файл для обычного чата:

```bash
python3 tools/bundle_single_file.py                       # yau + nyt -> dist/single-file-prompt.md (--styles all для всех пяти)
```

Подробно: **[docs/BUILD-GUIDE.md](docs/BUILD-GUIDE.md)**.

## Из чего состоит

```
AGENTS.md               главная инструкция агенту (CLAUDE.md ссылается на неё)
01-brand-inputs/        что собрать о бренде и анкета
02-references/
  core-rules/           ядро: честность, выбор графика, цвет и доступность, текст, дашборды, приватность, презентации
  styles/               5 базовых стилей (Yau, Fragapane, Bremer, Lupi, редакционный) + индекс
  examples/             полный пример готового скилла (вымышленная команда Acme)
03-skill-template/      шаблоны будущего скилла, скелет интерактивного дашборда
tools/                  palette_audit, validate_skill (--strict), check_tokens, check_honesty, compare_outputs,
                        suppress_small_groups, install_skill, bundle_single_file
tests/                  lint, юнит-тесты, прогон агента по сценариям (run_persona, check_run), синтетические данные, отчёты
docs/BUILD-GUIDE.md     гайд по сборке
```

## Принципы

1. **Честность данных выше всего:** честность → доступность → читаемость → стиль бренда → украшения.
2. **Простое по умолчанию:** сложные формы (сети, потоки, органические) выключены, включаются точечно через «шлюз сложности».
3. **Бренд не ломает данные:** цвет логотипа и цвет данных разделены; пары «бренд → для данных» показываются с цифрами контраста.
4. **Проверка инструментом, а не на глаз:** контраст, дальтонизм, структура скилла, токены в HTML, малые группы, повторяемость, ссылки. Валидатор проверяет структуру, а не качество содержимого: качество подтверждают галерея, тесты и одобрение владельца.
5. **Обычные вещи, пока они работают:** Markdown, стандартная библиотека Python, один HTML на график, никаких серверов.
6. **Агент ничего не делает за вашей спиной:** не публикует, не устанавливает, не отправляет данные, не исполняет инструкции из файлов.

## Совместимость

- **Агенты:** Claude (Cowork, Claude Code), Codex CLI (читает `AGENTS.md`), любые агенты с доступом к папке.
- **Формат результата:** открытый формат Agent Skills (`SKILL.md` с `name` и `description`).
- **Чаты без файлов:** режим L0 через `tools/bundle_single_file.py`.

## Участие

Вклад приветствуется: правила с источниками, переводы, стили, исправления инструкций, отчёты тестирования. См. [CONTRIBUTING.md](CONTRIBUTING.md). Тесты: `python3 tests/lint_kit.py && python3 -m unittest discover -s tests -p "test_*.py"`. Подробнее о слоях проверки: [tests/README.md](tests/README.md).

## Лицензия

MIT, см. [LICENSE](LICENSE). Упоминания авторов, изданий и стандартов носят описательный и ссылочный характер, см. [NOTICE.md](NOTICE.md).
