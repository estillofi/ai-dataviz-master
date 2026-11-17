#!/usr/bin/env python3
"""
Скрытие малых групп с дополнительным подавлением (без внешних библиотек).

Проблема: одной пометки «мало данных» мало. Если скрыта одна группа, а общий итог показан, её значение
восстанавливается вычитанием. Если скрытые группы объединены в «Другое», но их сумма сама меньше порога,
малая группа тоже опознаётся. Этот инструмент для одномерной таблицы «категория: число людей» решает обе задачи.

Алгоритм (порог k):
  1. Скрыть все группы с числом меньше k.
  2. Пока скрыта ровно одна группа или сумма скрытых меньше k, скрыть следующую по малости группу.
  3. Скрытые группы показываются только суммой «Другое» (она не меньше k и объединяет не меньше двух групп).
  4. Если после шагов показывать нечего (всё скрыто), разбивка не публикуется, остаётся только общий итог
     (если он сам не меньше k).

Ограничения (важно):
  * Работает для ОДНОГО среза. Для двумерных таблиц, нескольких фильтров и пересекающихся срезов применяй порог
    к каждой комбинации, либо убери фильтры, которые дробят данные на малые группы. Иначе вычитанием между срезами
    группа может быть восстановлена.
  * Это защита от очевидного раскрытия, а не формальная гарантия приватности.

Запуск:
  python3 tools/suppress_small_groups.py --csv таблица.csv --group-col class --count-col n --k 5
  python3 tools/suppress_small_groups.py --pairs "7А=14" "7Б=12" "8Б=2" --k 5
CSV: первая строка заголовок; число людей в столбце --count-col (целые, > 0).
"""
import argparse, csv, json, sys

def suppress(counts, k=5):
    """counts: dict группа -> число. Возвращает dict с полями shown, other, hidden, total, publishable_breakdown, notes."""
    if k < 2: raise ValueError("порог k должен быть не меньше 2")
    clean = {}
    for g, v in counts.items():
        if v is None or v < 0 or int(v) != v: raise ValueError(f"группа {g!r}: число людей должно быть целым неотрицательным, получено {v!r}")
        clean[g] = int(v)
    total = sum(clean.values()); notes = []
    hidden = {g for g, v in clean.items() if v < k}
    order = sorted(clean, key=lambda g: (clean[g], str(g)))
    def hidden_sum(): return sum(clean[g] for g in hidden)
    while hidden and (len(hidden) == 1 or hidden_sum() < k):
        rest = [g for g in order if g not in hidden]
        if not rest: break
        hidden.add(rest[0])
        notes.append(f"дополнительно скрыта группа {rest[0]!r}: иначе скрытое восстанавливается из итога")
    shown = {g: v for g, v in clean.items() if g not in hidden}
    other = hidden_sum() if hidden else 0
    breakdown = bool(shown)
    if hidden and (len(hidden) < 2 or other < k):
        # всё равно нельзя показать «Другое»: слишком мало данных
        notes.append("скрытые группы вместе меньше порога: «Другое» не публикуется")
        other = None
    if not breakdown:
        notes.append("разбивка по группам не публикуется: остаются только общий итог" + ("" if total >= k else " (и он меньше порога: не публиковать вообще)"))
    return {"k": k, "total": total if total >= k else None, "shown": shown, "other": other,
            "hidden": sorted(hidden, key=str), "publishable_breakdown": breakdown, "notes": notes}

def main():
    ap = argparse.ArgumentParser(description="Скрытие малых групп с дополнительным подавлением")
    ap.add_argument('--csv'); ap.add_argument('--group-col'); ap.add_argument('--count-col')
    ap.add_argument('--pairs', nargs='*', help='группа=число, например 7А=14')
    ap.add_argument('--k', type=int, default=5, help='порог (по умолчанию 5)')
    ap.add_argument('--json', action='store_true', help='вывод в JSON')
    a = ap.parse_args()
    counts = {}
    try:
        if a.pairs:
            for p in a.pairs:
                g, _, v = p.rpartition('=')
                if not g: ap.error(f"неверная пара {p!r}: нужен формат группа=число")
                counts[g] = int(v)
        elif a.csv and a.group_col and a.count_col:
            with open(a.csv, encoding='utf-8', newline='') as fh:
                for row in csv.DictReader(fh): counts[row[a.group_col]] = counts.get(row[a.group_col], 0) + int(row[a.count_col])
        else:
            ap.error("нужен --pairs или --csv с --group-col и --count-col")
        res = suppress(counts, a.k)
    except (ValueError, KeyError) as e:
        print(f"Ошибка: {e}", file=sys.stderr); return 2
    if a.json:
        print(json.dumps(res, ensure_ascii=False, indent=2)); return 0
    print(f"Порог k = {res['k']}. Общий итог: {res['total'] if res['total'] is not None else 'не публиковать'}")
    print("Показывать:", ", ".join(f"{g}: {v}" for g, v in res['shown'].items()) or "ничего")
    print("Другое:", res['other'] if res['other'] is not None else "не публиковать")
    print("Скрыто:", ", ".join(map(str, res['hidden'])) or "ничего")
    for n in res['notes']: print("  -", n)
    return 0

if __name__ == '__main__':
    sys.exit(main())
