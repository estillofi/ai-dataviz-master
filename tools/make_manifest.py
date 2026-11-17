#!/usr/bin/env python3
"""
Манифест контрольных сумм набора (без внешних библиотек).

Зачем: чтобы тестировщик или пользователь мог убедиться, что у него ТОТ САМЫЙ снимок набора, целый и неизменённый,
а не старая копия или папка, куда скопировали только часть файлов.

Манифест MANIFEST.sha256: строки «sha256  путь» для всех файлов набора, кроме материалов и результатов работы
(00-session/state.md, 01-brand-inputs/assets/, 04-output/, 05-research-log/, tests/reports/, dist/, .git, __pycache__)
и самого манифеста.

Запуск:
  python3 tools/make_manifest.py            # пересобрать MANIFEST.sha256 (делает мейнтейнер перед выпуском)
  python3 tools/make_manifest.py --check    # сверить текущие файлы с манифестом (код 1 при расхождениях)
"""
import hashlib, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MANIFEST = os.path.join(ROOT, 'MANIFEST.sha256')
SKIP_DIRS = {'.git', '__pycache__', 'node_modules', 'dist'}
SKIP_PREFIXES = ('00-session/state.md', '01-brand-inputs/assets/', '04-output/', '05-research-log/', 'tests/reports/')
SKIP_KEEP = {'01-brand-inputs/assets/.gitkeep', '04-output/README.md', '05-research-log/README.md', 'tests/reports/.gitkeep', 'tests/reports/README.md'}

def tracked_files(root=ROOT):
    out = []
    for r, ds, fs in os.walk(root):
        ds[:] = sorted(d for d in ds if d not in SKIP_DIRS)
        for f in sorted(fs):
            p = os.path.join(r, f); rel = os.path.relpath(p, root).replace(os.sep, '/')
            if rel == 'MANIFEST.sha256' or f.endswith('.pyc') or f in ('.DS_Store', 'Thumbs.db'): continue
            if rel.startswith(SKIP_PREFIXES) and rel not in SKIP_KEEP: continue
            out.append(rel)
    return sorted(out)

def sha(path):
    h = hashlib.sha256()
    with open(path, 'rb') as fh:
        for chunk in iter(lambda: fh.read(65536), b''): h.update(chunk)
    return h.hexdigest()

def build(root=ROOT):
    return {rel: sha(os.path.join(root, rel)) for rel in tracked_files(root)}

def read_manifest(path=MANIFEST):
    out = {}
    with open(path, encoding='utf-8') as fh:
        for line in fh:
            line = line.rstrip('\n')
            if not line.strip(): continue
            digest, _, rel = line.partition('  ')
            out[rel] = digest
    return out

def compare(root=ROOT, manifest_path=MANIFEST):
    """Возвращает (изменены, отсутствуют, лишние)."""
    m = read_manifest(manifest_path); cur = build(root)
    changed = sorted(p for p in m if p in cur and cur[p] != m[p])
    missing = sorted(p for p in m if p not in cur)
    extra = sorted(p for p in cur if p not in m)
    return changed, missing, extra

def main():
    if '--check' in sys.argv:
        if not os.path.isfile(MANIFEST): print("Нет MANIFEST.sha256: снимок неполный или собран не по правилам", file=sys.stderr); return 2
        changed, missing, extra = compare()
        for lab, items in (('ИЗМЕНЕНЫ', changed), ('ОТСУТСТВУЮТ', missing), ('ЛИШНИЕ (нет в манифесте)', extra)):
            if items: print(f"{lab}: {len(items)}"); [print('  ', i) for i in items[:20]]
        ok = not (changed or missing or extra)
        print("Манифест совпадает." if ok else "Манифест НЕ совпадает.")
        return 0 if ok else 1
    m = build()
    with open(MANIFEST, 'w', encoding='utf-8', newline='\n') as fh:
        for rel in sorted(m): fh.write(f"{m[rel]}  {rel}\n")
    print(f"Записан {MANIFEST}: {len(m)} файлов"); return 0

if __name__ == '__main__':
    sys.exit(main())
