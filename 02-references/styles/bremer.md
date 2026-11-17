# Правила визуализации данных: стиль Nadieh Bremer (Visual Cinnamon), «интерактивный нео-футуризм»

## 0. Как использовать этот файл

Файл прикрепляется к данным (CSV, XLSX, JSON, таблица в тексте). Claude обязан:

1. Прочитать данные и найти главный инсайт (один на фигуру).
2. Выбрать форму по разделу 5.
3. Выдать **один самодостаточный HTML-файл** (всё inline, без внешних стилей).
4. Применить все правила ниже. Если **стилевое** правило (цвет, шрифт, форма подписи, раскладка) конфликтует с запросом пользователя, приоритет у запроса: сообщи об этом одной строкой. **Правила честности данных запрос пользователя не отменяет:** столбцы от нуля, без двойных осей, 3D и круговых диаграмм, без подгонки вывода и скрытия данных. На такую просьбу объясни в одну-две фразы и сделай честную замену. Предупреждение не делает нечестный график допустимым, «оба варианта» не делай.
5. Прогнать чек-лист раздела 12 до выдачи.

Если инсайт неочевиден или историй несколько, выбери одну сам, назови её в ответе и спроси, нужна ли другая. Не задавай вопросов до первой версии.

Формат ответа после генерации: файл + 3-4 строки: какой инсайт и какая форма выбраны и почему, что в данных было нестандартного (пропуски, выбросы, агрегации).

### Когда использовать

Сложные связи и потоки: сетевая архитектура, микросервисы, блокчейн-транзакции, нейросети, цепочки поставок, миграции, коллаборации. Плотные данные, где зритель исследует, а не быстро проверяет значение. Экран, а не печать в ч/б.

Не использовать: быстрые решения по точным цифрам (берите Yau), ч/б печать, < 4 или > 20 групп без агрегации.

---

## 1. Основания (что подтверждено исследованием, где бриф шире источников)

| Приём | Что известно | Как применяем |
|---|---|---|
| Свечение (glow) | В её туториале: размытая копия формы кладётся под оригинал (`feGaussianBlur` + `feMerge`); `stdDeviation` ~2.5-3.5 регулирует рассеяние | Фильтр на группах, не на каждом элементе |
| Смешение цветов | `mix-blend-mode: screen` на тёмном фоне, `multiply` на светлом. На «чужом» фоне ничего не видно. Нужен `isolation: isolate` на группе. Использует при частичном перекрытии равноценных объектов | Ленты в `screen` внутри изолированной группы |
| Градиент по данным | Градиент ленты chord-диаграммы ориентирован от источника к получателю, цвета концов = цвета групп | `linearGradient` с `gradientUnits="userSpaceOnUse"` |
| Интерактив | Её chord-примеры подсвечивают связи по наведению | Hover и focus: остальное приглушается |
| Процесс | Данные → эскиз → код; думать не «какой график», а «какой образ выражает мысль»; привлекательность — первый барьер, но не вместо эффективности | Эскиз структуры до кода, красота служит чтению |
| Тёмный фон | **Бриф шире источников.** Тёмный неон — одна из её эстетик, в части примеров и туториалов фон светлый | Тёмная схема по умолчанию, светлый вариант в разделе 3 |

## 2. Принципы

1. **Эффективно и красиво.** Красота привлекает, структура объясняет. Если эффект мешает чтению, эффект убирается.
2. **Свечение — акцент, не данные.** Glow выделяет главное. Интенсивность свечения никогда не кодирует значение.
3. **Поток виден.** Ширина = объём, цвет течёт от источника к получателю.
4. **Живое, но управляемое.** Hover/focus-подсветка, мягкие переходы. Никакого мерцания, автоплея и тяжёлых анимаций.
5. **Плотность с иерархией.** Много связей допустимо, но главное видно с первого взгляда, остальное приглушено.
6. **Честный минимум.** Значения топ-связей подписаны, полные данные доступны таблицей.

## 3. Токены

### 3a. Основная схема (тёмный неон)

```css
:root {
  --bg: #0B1020;                 /* глубокий charcoal-navy */
  --bg-glow: #16204A;            /* центр мягкого радиального свечения фона */
  --ring: rgba(150, 170, 215, .16);

  /* неоновые категории: не больше 5, порядок фиксирован */
  --c1: #00E5FF;                 /* electric cyan */
  --c2: #FF2BD6;                 /* magenta */
  --c3: #FFE600;                 /* bright yellow */
  --c4: #8C6BFF;                 /* violet */
  --c5: #3CFFB0;                 /* mint */

  --text-title: #F2F6FF;
  --text-body: #C9D4EA;
  --text-muted: #8493B0;         /* ~6:1 на --bg */
  --font: "Manrope", Arial, sans-serif;   /* файл и @font-face: ../fonts/README.md */
}
```

### 3b. Светлый вариант (если экран или проектор яркий)

`--bg: #F5F3EE`, категории темнее (`--c1: #008FB3; --c2: #C2189E; --c3: #C99A00; --c4: #5B3FD1; --c5: #00A86B`), у лент `mix-blend-mode: multiply` вместо `screen`, свечение убрать (на светлом фоне оно не читается), контур дуг `1px` темнее заливки.

## 4. Типографика

| Элемент | Размер | Вес | Цвет |
|---|---|---|---|
| Заголовок (вывод) | 30px (моб. 24px) | 600, `letter-spacing: -.01em` | `--text-title` |
| Подзаголовок | 15px | 400 | `--text-body` |
| Метки групп | 12px, uppercase, `letter-spacing: .08em` | 600 | `--text-title` |
| Значения, ключ, оси | 11px, `tabular-nums` | 400 | `--text-muted` |
| Источник, примечания | 12px | 400 | `--text-muted` |

Только sans-serif. Текст не светится (никакого glow на подписях). Контраст текста на тёмном фоне ≥ 7:1 для основных подписей, ≥ 4.5:1 для вторичных.

## 5. Формы (метафора под структуру данных)

| Данные | Форма |
|---|---|
| Матрица связей/потоков между 4-20 группами | **Chord-диаграмма** (скелет в разделе 11) |
| Поток через стадии (воронка, миграция, этапы пайплайна) | **Sankey / alluvial** |
| Сеть узлов (зависимости, граф, блокчейн) | **Созвездие**: светящиеся узлы, тонкие дуги с градиентом, размер узла = значение |
| Временной ряд многих сущностей | Радиальные или плавные линии с градиентом по значению |
| Кластеры, распределения | Bubble-кластеры или beeswarm с glow на выделенной группе |

Если форма с эффектами хуже читается, чем простая, выбирай простую. Стиль можно нести цветом, фоном и свечением на обычном графике.

## 6. Техники (проверенные рецепты)

**Glow** (один фильтр, на группе):

```html
<filter id="glow" x="-30%" y="-30%" width="160%" height="160%">
  <feGaussianBlur stdDeviation="3.5" result="blur"/>
  <feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge>
</filter>
<g filter="url(#glow)"> … главные дуги/узлы … </g>
```

Правила: `stdDeviation` 2.5-4; фильтр на ≤ нескольких группах, не на сотнях элементов (производительность); не на тексте и не на тонких сетках; область фильтра с запасом `x/y/width/height`, иначе свечение обрежется.

**Blend:**

```css
.ribbons { isolation: isolate; }          /* без этого screen даст белый экран */
.ribbon  { mix-blend-mode: screen; fill-opacity: .65; }   /* на светлом фоне: multiply */
```

Blend использовать при **частичном** перекрытии равноценных объектов. Если ленты перекрываются почти целиком, снизь число или прозрачность, иначе всё сольётся.

**Градиент ленты по данным:** по одному `linearGradient` на ленту, `gradientUnits="userSpaceOnUse"`, точки `x1,y1` и `x2,y2` = середины срезов источника и получателя на кольце. Стопы: цвет источника → цвет получателя.

**Слои (снизу вверх):** фон с радиальным свечением → структурные кольца (пунктир) → ленты (изолированная группа) → внешние дуги (glow) → подписи → ключ.

**Интерактив:** hover и focus на дуге/узле: связанные элементы остаются, остальные `opacity: .12`. Все интерактивные элементы доступны с клавиатуры (`tabindex="0"`). Контент читается и без hover.

**Анимация:** по умолчанию только переходы opacity (.15s). Допустимо одно появление «draw-in» ≤ 1.2 с и один пульс на выделенном элементе, отключаемые через `@media (prefers-reduced-motion: reduce)`. Мерцание > 3 раз в секунду запрещено.

## 7. Кодирование и честность

- Ширина ленты ∝ значению. Для симметричной матрицы концы равны. Для направленных потоков (A→B ≠ B→A) ширина на источнике = исходящий объём, на получателе = входящий.
- Длина дуги группы ∝ сумме её потоков.
- Размер узла в сети ∝ значению через площадь (`r = k·√v`).
- Минимальная видимая ширина ленты 1px. Нулевые потоки не рисуются.
- Chord и glow плохо подходят для точного чтения. Поэтому обязательно: подписаны суммы групп, топ-связи имеют `<title>`/tooltip, полные данные в `<details>` с таблицей.
- Групп ≤ 20. Остальное агрегируется в «Другое» с примечанием.
- Цвет несёт только категорию. Не использовать пару красный/зелёный как единственное различие. Различие дублируется подписью и положением.
- Яркость, свечение и размер эффектов не должны выглядеть как кодирование значения. Если свечение выделяет главный элемент, объясни это в ключе.

## 8. Подписи и ключ «Как читать»

- Подписи у дуг: название (uppercase) + сумма. Не на лентах, не внутри кольца.
- Ключ обязателен, компактный (3 строки): «цвет течёт от источника к получателю», «ширина = объём (ед.)», «наведи на дугу: связи группы».
- Заголовок = вывод с числом («60% трафика проходит через один шлюз»).
- Источник и примечания обязательны.

## 9. Композиция

- Контейнер `max-width: 1000px`, фигура на радиальном фоне `--bg-glow → --bg`, скругление 16px.
- Фигура квадратная или 1000×820, воздух вокруг не меньше 8%.
- Адаптив: SVG `viewBox`, на < 600px убрать вторичные подписи, оставить заголовок, фигуру, ключ под ней.

## 10. Технические требования

- Один HTML-файл, CSS и JS внутри. Рендер: inline SVG на ванильном JS (скелет ниже). D3 допустим с `https://cdnjs.cloudflare.com/ajax/libs/d3/7.9.0/d3.min.js` (версия зафиксирована). Для > ~1500 элементов использовать Canvas или снижать детализацию.
- Данные константой `const …` в начале скрипта. Цвета через CSS-переменные.
- Шрифты: Manrope — локальные файлы из `../fonts/` через `@font-face` (в скилле — `assets/fonts/`) и запасной стек; сетевые шрифты не подключать.
- Доступность: `role="img"`, `<title>`, `<desc>`, таблица данных в `<details>`, фокус с клавиатуры.
- Без localStorage, внешних запросов, счётчиков. Размер файла до 300 КБ.
- Типографика текста: «ёлочки», ’, длинное тире.

## 11. Скелет (проверен в браузере)

Chord-диаграмма с градиентными лентами, glow-дугами, hover/focus, ключом и таблицей данных.

```html
<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>ЗАГОЛОВОК-ВЫВОД</title>
<style>
  :root{
    --bg:#0B1020; --bg-glow:#16204A; --ring:rgba(150,170,215,.16);
    --c1:#00E5FF; --c2:#FF2BD6; --c3:#FFE600; --c4:#8C6BFF; --c5:#3CFFB0;
    --text-title:#F2F6FF; --text-body:#C9D4EA; --text-muted:#8493B0;
    --font:"Manrope",Arial,sans-serif;
  }
  *{box-sizing:border-box}
  html,body{margin:0;background:var(--bg);color:var(--text-body);font-family:var(--font)}
  main{max-width:1000px;margin:0 auto;padding:40px 20px 56px}
  h1{font-size:30px;line-height:1.2;font-weight:600;letter-spacing:-.01em;color:var(--text-title);margin:0 0 8px}
  .sub{font-size:15px;line-height:1.5;margin:0 0 20px;max-width:64ch}
  #stage{background:radial-gradient(circle at 50% 48%,var(--bg-glow) 0%,var(--bg) 68%);border-radius:16px}
  svg{display:block;width:100%;height:auto}
  .ring{fill:none;stroke:var(--ring);stroke-width:.75;stroke-dasharray:1 5;stroke-linecap:round}
  .ribbons{isolation:isolate}
  .ribbon{mix-blend-mode:screen;fill-opacity:.65;stroke:rgba(255,255,255,.18);stroke-width:.5;transition:fill-opacity .15s,opacity .15s}
  .arc{fill:none;stroke-width:10;transition:opacity .15s;outline:none}
  .lbl{font:600 12px var(--font);letter-spacing:.08em;text-transform:uppercase;fill:var(--text-title)}
  .val{font:11px var(--font);fill:var(--text-muted);font-variant-numeric:tabular-nums}
  .dim{opacity:.12}
  footer{font-size:12px;color:var(--text-muted);margin-top:14px;line-height:1.5}
  details{margin-top:12px;font-size:12px;color:var(--text-muted)}
  table{border-collapse:collapse;margin-top:8px}
  td,th{padding:3px 10px;border-bottom:1px solid var(--ring);text-align:right}
  @media (max-width:600px){h1{font-size:24px}}
</style>
</head>
<body>
<main>
  <h1>Заголовок-вывод: что и куда течёт</h1>
  <p class="sub">Что измерено, единицы, период. Ширина ленты = объём потока, цвет течёт от источника к получателю.</p>
  <div id="stage">
    <svg id="fig" viewBox="0 0 1000 820" role="img" aria-labelledby="t d">
      <title id="t">Заголовок-вывод</title>
      <desc id="d">Текстовое описание: главные потоки и вывод.</desc>
      <defs>
        <filter id="glow" x="-30%" y="-30%" width="160%" height="160%">
          <feGaussianBlur stdDeviation="3.5" result="blur"/>
          <feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge>
        </filter>
      </defs>
      <g id="layer-rings"></g><g id="layer-grads"></g>
      <g id="layer-ribbons" class="ribbons"></g>
      <g id="layer-arcs" filter="url(#glow)"></g>
      <g id="layer-labels"></g><g id="layer-key"></g>
    </svg>
  </div>
  <footer>Источник: … · Примечание: …</footer>
  <details><summary>Данные таблицей</summary><table id="tbl"></table></details>
</main>
<script>
const NAMES = ["API", "База", "Кэш", "Очередь", "Клиент"];
const COLORS = ["var(--c1)", "var(--c2)", "var(--c3)", "var(--c4)", "var(--c5)"];
// до 5 категорий (оттенки --c1…--c5)
// симметричная матрица потоков: M[i][j] = M[j][i], диагональ 0
const M = [
  [0, 40, 22, 10, 55],
  [40, 0, 18, 8, 6],
  [22, 18, 0, 5, 12],
  [10, 8, 5, 0, 14],
  [55, 6, 12, 14, 0]
];

const NS = "http://www.w3.org/2000/svg";
const el = (tag, attrs = {}, parent) => {
  const n = document.createElementNS(NS, tag);
  for (const k in attrs) n.setAttribute(k, attrs[k]);
  if (parent) parent.appendChild(n);
  return n;
};
const $ = id => document.getElementById(id);
const cx = 500, cy = 400, R = 290, GAP = 0.06;
const P = (r, a) => [cx + r * Math.cos(a), cy + r * Math.sin(a)];

// --- раскладка: угол группы ∝ сумме её потоков, срез ленты ∝ значению
const n = NAMES.length;
const rowSum = M.map(r => r.reduce((s, v) => s + v, 0));
const k = (2 * Math.PI - n * GAP) / rowSum.reduce((s, v) => s + v, 0);
const groups = [], slice = M.map(() => []);
let a = -Math.PI / 2;
for (let i = 0; i < n; i++) {
  const a0 = a; let s = a;
  for (let j = 0; j < n; j++) { slice[i][j] = [s, s + M[i][j] * k]; s += M[i][j] * k; }
  groups.push({ a0, a1: s }); a = s + GAP;
}

// --- структурные кольца
[.33, .66, 1].forEach(f => el("circle", { cx, cy, r: R * f, class: "ring" }, $("layer-rings")));

// --- ленты с градиентом от источника к получателю (userSpaceOnUse)
for (let i = 0; i < n; i++) for (let j = i + 1; j < n; j++) {
  if (!M[i][j]) continue;
  const [s0, s1] = slice[i][j], [t0, t1] = slice[j][i], id = `g-${i}-${j}`;
  const [x1, y1] = P(R, (s0 + s1) / 2), [x2, y2] = P(R, (t0 + t1) / 2);
  const g = el("linearGradient", { id, gradientUnits: "userSpaceOnUse", x1, y1, x2, y2 }, $("layer-grads"));
  el("stop", { offset: "0%", style: `stop-color:${COLORS[i]}` }, g);
  el("stop", { offset: "100%", style: `stop-color:${COLORS[j]}` }, g);
  const d = `M${P(R, s0)}A${R},${R} 0 0 1 ${P(R, s1)}Q${cx},${cy} ${P(R, t0)}A${R},${R} 0 0 1 ${P(R, t1)}Q${cx},${cy} ${P(R, s0)}Z`;
  const r = el("path", { d, fill: `url(#${id})`, class: "ribbon", "data-i": i, "data-j": j }, $("layer-ribbons"));
  const tip = el("title", {}, r); tip.textContent = `${NAMES[i]} ↔ ${NAMES[j]}: ${M[i][j]}`;
}

// --- внешние дуги (свечение через общий фильтр на группе)
groups.forEach((g, i) => {
  const rr = R + 14, large = (g.a1 - g.a0) > Math.PI ? 1 : 0;
  el("path", { d: `M${P(rr, g.a0)}A${rr},${rr} 0 ${large} 1 ${P(rr, g.a1)}`, class: "arc", stroke: COLORS[i], "data-i": i }, $("layer-arcs"));
  const mid = (g.a0 + g.a1) / 2, [lx, ly] = P(R + 40, mid), right = Math.cos(mid) >= 0;
  const t = el("text", { x: lx, y: ly, class: "lbl", "text-anchor": right ? "start" : "end", "dominant-baseline": "middle" }, $("layer-labels"));
  t.textContent = NAMES[i];
  const v = el("text", { x: lx, y: ly + 15, class: "val", "text-anchor": right ? "start" : "end" }, $("layer-labels"));
  v.textContent = rowSum[i];
});

// --- hover: подсветить связи группы, остальное приглушить
const rib = [...document.querySelectorAll(".ribbon")], arcs = [...document.querySelectorAll(".arc")];
arcs.forEach(arc => {
  const i = +arc.dataset.i;
  const on = () => { rib.forEach(r => r.classList.toggle("dim", +r.dataset.i !== i && +r.dataset.j !== i));
                     arcs.forEach(o => o.classList.toggle("dim", +o.dataset.i !== i)); };
  const off = () => [...rib, ...arcs].forEach(o => o.classList.remove("dim"));
  arc.setAttribute("tabindex", "0");                       // доступность: то же самое с клавиатуры
  arc.addEventListener("mouseenter", on); arc.addEventListener("focus", on);
  arc.addEventListener("mouseleave", off); arc.addEventListener("blur", off);
});

// --- ключ «Как читать»
const K = $("layer-key"), kx = 60, ky = 735;
const kg = el("linearGradient", { id: "keyg", gradientUnits: "userSpaceOnUse", x1: kx, y1: 0, x2: kx + 180, y2: 0 }, $("layer-grads"));
el("stop", { offset: "0%", style: "stop-color:var(--c1)" }, kg); el("stop", { offset: "100%", style: "stop-color:var(--c2)" }, kg);
el("path", { d: `M${kx},${ky} C${kx + 60},${ky - 18} ${kx + 120},${ky + 18} ${kx + 180},${ky}`, fill: "none", stroke: "url(#keyg)", "stroke-width": 8, "stroke-linecap": "round" }, K);
el("circle", { cx: kx, cy: ky, r: 4, fill: "var(--c1)" }, K); el("circle", { cx: kx + 180, cy: ky, r: 4, fill: "var(--c2)" }, K);
[["цвет течёт от источника к получателю", 28], ["ширина = объём потока (ед.)", 44], ["наведи на дугу: связи группы", 60]].forEach(([s, dy]) => {
  const t = el("text", { x: kx, y: ky + dy, class: "val" }, K); t.textContent = s;
});

// --- таблица данных для доступности
$("tbl").innerHTML = "<tr><th></th>" + NAMES.map(x => `<th>${x}</th>`).join("") + "</tr>" +
  M.map((r, i) => `<tr><th>${NAMES[i]}</th>${r.map(v => `<td>${v}</td>`).join("")}</tr>`).join("");
</script>
</body>
</html>
```

## 12. Чек-лист

**Данные**
- [ ] Ширина ленты ∝ значению, длина дуги ∝ сумме.
- [ ] Групп ≤ 20, остальное в «Другое».
- [ ] Суммы подписаны, таблица данных есть, значения доступны.
- [ ] Свечение не кодирует значение.

**Эстетика**
- [ ] Тёмный фон с мягким радиальным свечением (или светлый вариант с multiply).
- [ ] ≤ 5 оттенков категорий.
- [ ] Ленты полупрозрачные, `isolation: isolate`, `screen` на тёмном.
- [ ] Glow на группе главных дуг, не на тексте.

**Интерактив и техника**
- [ ] Hover и focus подсвечивают связи, остальное приглушено.
- [ ] `prefers-reduced-motion` учтён, мерцания нет.
- [ ] Контраст текста ≥ 7:1 (основной), ≥ 4.5:1 (вторичный).
- [ ] Один HTML-файл, 375px и 1280px проверены.

## 13. Антипаттерны

- Радужные хаотичные градиенты без связи с данными.
- Свечение на всём подряд, включая текст и сетку.
- `screen` на светлом фоне (ничего не видно) или без `isolation`.
- Chord для 40 групп без агрегации.
- Интенсивность свечения как «значение».
- Автоплей анимации, мерцание, вращение фигуры без причины.
- Красный и зелёный как единственное различие категорий.
- Неон в слайдах, которые будут печататься в ч/б.
- Фигура без ключа и без доступной таблицы данных.

## 14. Быстрые запросы (вместе с файлом)

- «Визуализируй по правилам. Форму выбери сам.»
- «Chord по матрице, направленные потоки, главный поток выдели акцентом.»
- «Светлый вариант для печати.»

