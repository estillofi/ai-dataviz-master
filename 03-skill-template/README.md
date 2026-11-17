# Шаблон скилла

Агент берёт эти файлы как основу, подставляет решения владельца (всё в `{{ДВОЙНЫХ_СКОБКАХ}}`) и кладёт результат в `04-output/<slug>-dataviz/`.

| Файл | Куда идёт в скилле | Что подставить |
|---|---|---|
| `SKILL.template.md` | `SKILL.md` | Название, описание-триггер, таблица выбора стиля |
| `references/house-style.template.md` | `references/house-style.md` | Решения команды из этапов 3-4 |
| `references/brand-tokens.template.md` | `references/brand-tokens.md` | Палитра данных и результаты аудита |
| `references/chart-catalog.template.md` | `references/chart-catalog.md` | Отличия команды от базового каталога |
| `references/dashboard-patterns.template.md` | `references/dashboard-patterns.md` | Метрики, фильтры, раскладка из этапа 5 |
| `references/presentation-rules.template.md` | `references/presentation-rules.md` | Значения из этапа 6 |
| `references/glossary.template.md` | `references/glossary.md` | Глоссарий метрик |
| `assets/tokens.template.css` | `assets/tokens.css` | Токены |
| `assets/dashboard-skeleton.html` | `assets/dashboard-skeleton.html` | Блок `:root` заменить токенами команды |
| `evals.template.md` | `evals/evals.md` | Метрики владельца в тестах |

Не меняй: `02-references/core-rules/*` копируется в `references/core/` дословно. Базовые стили копируются из `02-references/styles/` (только выбранные).

## Описание-триггер: образец (до 1024 символов)

```
Создаёт графики, диаграммы, дашборды, KPI-карточки и интерактивные визуализации, а также оформляет данные в презентациях, слайдах, отчётах и документах для {{КОМАНДА}} в фирменном стиле и по строгим правилам честной визуализации. Используй ВСЕГДА, когда просят график, диаграмму, дашборд, визуализацию, инфографику, «покажи на графике», «сделай слайд с цифрами», презентацию или отчёт с данными, метриками или таблицами, даже если слово «график» не названо. Use for any chart, dashboard, KPI card, data visualization, or slides and reports containing data. Не используй для простых таблиц без визуализации.
```

В YAML значение берётся в двойные кавычки: двоеточие с пробелом внутри ломает разбор.
