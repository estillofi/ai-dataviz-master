#!/usr/bin/env python3
"""
Аудит палитры для визуализации данных (без внешних библиотек).

Проверяет:
  1. Контраст WCAG 2.x: текст на фоне (>= 4.5:1), графика на фоне (>= 3:1).
  2. Различимость категориальных цветов при дальтонизме (протан, дейтан, тритан)
     по расстоянию в CIELAB (dE76). Порог предупреждения: dE < 10.
Это инструмент предупреждений, а не приговор: решение за человеком.

Запуск:
  python3 tools/palette_audit.py --bg "#FFFFFF" \
      --text "#1F2933" "#52606D" \
      --graphics "#0072B2" "#D55E00" \
      --categorical "#0072B2" "#E69F00" "#009E73" "#CC79A7" "#56B4E9" "#D55E00"
Или из JSON: python3 tools/palette_audit.py --json palette.json
  (ключи: bg, text[], graphics[], categorical[])
Опция --md отчёт.md сохраняет отчёт в файл.
Код возврата: 0 отчёт построен; 2 неверный ввод. Количество предупреждений смотри в последней строке отчёта.
"""
import argparse, json, math, re, sys

HEX_RE = re.compile(r'^#?(?:[0-9A-Fa-f]{3}|[0-9A-Fa-f]{6})$')

class ColorError(ValueError):
    """Неверный формат цвета."""

def check_hex(h):
    if not isinstance(h, str) or not HEX_RE.match(h.strip()):
        raise ColorError(f"неверный цвет {h!r}: нужен HEX вида #RGB или #RRGGBB, например #0072B2")
    return h.strip()

def hex_to_rgb(h):
    h = check_hex(h).lstrip('#')
    if len(h) == 3: h = ''.join(c*2 for c in h)
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))

def srgb_to_lin(c):
    c = c/255.0
    return c/12.92 if c <= 0.04045 else ((c+0.055)/1.055)**2.4

def lin_to_srgb(c):
    c = max(0.0, min(1.0, c))
    return 12.92*c if c <= 0.0031308 else 1.055*(c**(1/2.4))-0.055

def luminance(rgb):
    r, g, b = (srgb_to_lin(x) for x in rgb)
    return 0.2126*r + 0.7152*g + 0.0722*b

def contrast(a, b):
    la, lb = luminance(hex_to_rgb(a)), luminance(hex_to_rgb(b))
    hi, lo = max(la, lb), min(la, lb)
    return (hi+0.05)/(lo+0.05)

# Матрицы Machado, Oliveira, Fernandes (2009), severity 1.0, в линейном RGB
CVD = {
  'протан (красный)':  [[0.152286, 1.052583, -0.204868], [0.114503, 0.786281, 0.099216], [-0.003882, -0.048116, 1.051998]],
  'дейтан (зелёный)':  [[0.367322, 0.860646, -0.227968], [0.280085, 0.672501, 0.047413], [-0.011820, 0.042940, 0.968881]],
  'тритан (синий)':    [[1.255528, -0.076749, -0.178779], [-0.078411, 0.930809, 0.147602], [0.004733, 0.691367, 0.303900]],
}

def simulate(rgb, m):
    lin = [srgb_to_lin(x) for x in rgb]
    out = [sum(m[i][j]*lin[j] for j in range(3)) for i in range(3)]
    return tuple(255*lin_to_srgb(v) for v in out)

def to_lab(rgb):
    r, g, b = (srgb_to_lin(x) for x in rgb)
    X = 0.4124564*r + 0.3575761*g + 0.1804375*b
    Y = 0.2126729*r + 0.7151522*g + 0.0721750*b
    Z = 0.0193339*r + 0.1191920*g + 0.9503041*b
    xn, yn, zn = 0.95047, 1.0, 1.08883
    def f(t): return t**(1/3) if t > 0.008856 else 7.787*t + 16/116
    fx, fy, fz = f(X/xn), f(Y/yn), f(Z/zn)
    return (116*fy-16, 500*(fx-fy), 200*(fy-fz))

def dE(a, b):
    return math.dist(to_lab(a), to_lab(b))

def audit(cfg):
    bg = check_hex(cfg['bg'])
    for key in ('text', 'graphics', 'categorical'):
        for c in cfg.get(key, []): check_hex(c)
    if not any(cfg.get(k) for k in ('text', 'graphics', 'categorical')):
        raise ColorError("нечего проверять: укажи хотя бы один цвет в --text, --graphics или --categorical")
    lines = []; problems = 0
    lines.append(f"# Аудит палитры\n\nФон: `{bg}`\n")
    lines.append("## 1. Контраст на фоне\n")
    lines.append("| Цвет | Роль | Контраст | Порог | Результат |\n|---|---|---|---|---|")
    for c in cfg.get('text', []):
        r = contrast(c, bg); ok = r >= 4.5; problems += (not ok)
        lines.append(f"| `{c}` | текст | {r:.2f}:1 | 4.5 | {'ok' if ok else 'НЕ проходит'} |")
    for c in cfg.get('graphics', []):
        r = contrast(c, bg); ok = r >= 3.0; problems += (not ok)
        lines.append(f"| `{c}` | значимая графика | {r:.2f}:1 | 3.0 | {'ok' if ok else 'НЕ проходит (допустимо только для фонового контекста)'} |")
    cats = cfg.get('categorical', [])
    for c in cats:
        r = contrast(c, bg); ok = r >= 3.0; problems += (not ok)
        lines.append(f"| `{c}` | категория | {r:.2f}:1 | 3.0 | {'ok' if ok else 'слабый контраст: добавь подпись или обводку'} |")
    if len(cats) > 1:
        lines.append("\n## 2. Различимость категорий при дальтонизме (dE76, порог 10)\n")
        lines.append("| Тип | Пары с риском |\n|---|---|")
        for name, m in CVD.items():
            sim = [simulate(hex_to_rgb(c), m) for c in cats]
            risky = []
            for i in range(len(cats)):
                for j in range(i+1, len(cats)):
                    d = dE(sim[i], sim[j])
                    if d < 10: risky.append(f"`{cats[i]}` и `{cats[j]}` (dE {d:.1f})")
            problems += len(risky)
            lines.append(f"| {name} | {'; '.join(risky) if risky else 'нет'} |")
        lines.append("\nПри риске: не полагайся на цвет. Добавь прямую подпись, форму маркера, штриховку или положение.")
        too_many = len(cats) > 6
        problems += too_many
        lines.append(f"\nКатегорий: {len(cats)}. " + ("Больше 6: сократи или агрегируй («Другое»), либо используй small multiples." if too_many else "Количество приемлемо (до 6)."))
    lines.append(f"\n**Итого предупреждений: {problems}**")
    return "\n".join(lines), problems

def main():
    p = argparse.ArgumentParser(description="Аудит палитры: контраст WCAG и дальтонизм")
    p.add_argument('--bg'); p.add_argument('--text', nargs='*', default=[]); p.add_argument('--graphics', nargs='*', default=[])
    p.add_argument('--categorical', nargs='*', default=[]); p.add_argument('--json'); p.add_argument('--md')
    a = p.parse_args()
    if a.json:
        try:
            with open(a.json, encoding='utf-8') as fh: cfg = json.load(fh)
        except OSError as e:
            print(f"Ошибка: не прочитан {a.json}: {e}", file=sys.stderr); return 2
        except UnicodeError as e:
            print(f"Ошибка: {a.json} не в UTF-8: {e}", file=sys.stderr); return 2
        except json.JSONDecodeError as e:
            print(f"Ошибка: в {a.json} неверный JSON: {e}", file=sys.stderr); return 2
        if not isinstance(cfg, dict):
            print(f"Ошибка: в {a.json} ожидается объект JSON с ключами bg, text, graphics, categorical", file=sys.stderr); return 2
    else:
        cfg = {'bg': a.bg, 'text': a.text, 'graphics': a.graphics, 'categorical': a.categorical}
    if not cfg.get('bg'): p.error('нужен --bg или --json')
    try:
        report, n = audit(cfg)
    except ColorError as e:
        print(f"Ошибка: {e}", file=sys.stderr); return 2
    print(report)
    if a.md:
        try:
            with open(a.md, 'w', encoding='utf-8') as fh: fh.write(report + "\n")
        except OSError as e:
            print(f"Ошибка: не записан {a.md}: {e}", file=sys.stderr); return 2
    return 0

if __name__ == '__main__':
    sys.exit(main())
