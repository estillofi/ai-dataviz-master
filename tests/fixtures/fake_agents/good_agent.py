#!/usr/bin/env python3
"""Поддельный «хороший» агент для проверки харнеса: делает всё, что требует AGENTS.md, из образца Acme."""
import os, shutil
cwd = os.getcwd()
ex = os.path.join(cwd, '02-references', 'examples', 'acme-dataviz')
out = os.path.join(cwd, '04-output')
shutil.copytree(ex, os.path.join(out, 'acme-dataviz'))
gal = os.path.join(out, 'test-gallery'); os.makedirs(gal)
with open(os.path.join(ex, 'examples', 'dashboard-orders.html'), encoding='utf-8') as fh: golden = fh.read()
for n in ('dashboard', 'line', 'bars', 'table'):
    with open(os.path.join(gal, n + '.html'), 'w', encoding='utf-8') as fh: fh.write(golden)
with open(os.path.join(gal, 'slide.html'), 'w', encoding='utf-8') as fh:
    fh.write(golden.replace('<body>', '<body data-slide>', 1))
os.makedirs(os.path.join(cwd, '00-session'), exist_ok=True)
for rel, text in {'00-session/state.md': '# Состояние\n\nTBD: третья задача, шаблон презентации.\n',
                  '04-output/palette-audit.md': '# Аудит палитры\n\nПредупреждений: 0\n',
                  '04-output/handover.md': '# Передача\n\nЧто не проверено: повторяемость, подключение в новом чате.\n',
                  '01-brand-inputs/intake-form.md': '# Анкета\n\nзаполнено по ответам владельца\n'}.items():
    with open(os.path.join(cwd, rel), 'w', encoding='utf-8') as fh: fh.write(text)
print('good agent done')
