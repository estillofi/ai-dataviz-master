"""Шлюз честности (находка V-11, BLOCKER): должен ловить то, что реально выдал агент, и не ругаться на честные графики."""
import importlib.util, os, re, subprocess, sys, tempfile, unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
spec = importlib.util.spec_from_file_location('check_honesty', os.path.join(ROOT, 'tools', 'check_honesty.py'))
ch = importlib.util.module_from_spec(spec); spec.loader.exec_module(ch)

WRAP = '<html><body><h1>Заголовок</h1>{}<footer>Источник: тест</footer></body></html>'

TRUNCATED_BARS = WRAP.format('''<svg viewBox="0 0 400 300">
  <text x="10" y="250">5 млн</text><text x="10" y="170">6 млн</text><text x="10" y="90">7 млн</text>
  <rect x="60" y="150" width="40" height="100" fill="#888"/><rect x="120" y="110" width="40" height="140" fill="#888"/>
  <rect x="180" y="60" width="40" height="190" fill="#888"/></svg>''')
PIE_SECTORS = WRAP.format('''<svg viewBox="0 0 200 200">
  <path d="M100,100 L100,20 A80,80 0 0 1 180,100 Z" fill="#a00"/><path d="M100,100 L180,100 A80,80 0 0 1 100,180 Z" fill="#0a0"/>
  <path d="M100,100 L100,180 A80,80 0 1 1 100,20 Z" fill="#00a"/></svg>''')
PIE_CONIC = WRAP.format('<style>.c{width:200px;height:200px;border-radius:50%;background:conic-gradient(#a00 0 30%, #0a0 0 60%, #00a 0)}</style><div class="c"></div>')
DONUT = WRAP.format('''<svg viewBox="0 0 200 200"><circle cx="100" cy="100" r="60" fill="none" stroke="#a00" stroke-width="30" stroke-dasharray="120 257"/>
  <circle cx="100" cy="100" r="60" fill="none" stroke="#0a0" stroke-width="30" stroke-dasharray="100 277" stroke-dashoffset="-120"/></svg>''')
THREE_D = WRAP.format('<style>.b{transform:perspective(400px) rotateX(30deg)}</style><div class="b">столбцы</div>')
DECLARED_BAD = WRAP.format('<svg data-chart="bar" data-axis-min="5000000" viewBox="0 0 10 10"><rect width="1" height="1" fill="#000"/></svg>')
DUAL = WRAP.format('<svg data-chart="line" data-dual-axis="true" viewBox="0 0 10 10"></svg>')
HONEST_BARS = WRAP.format('''<svg data-chart="bar" data-axis-min="0" viewBox="0 0 400 300">
  <text x="10" y="250">0</text><text x="10" y="170">5 млн</text><text x="10" y="90">10 млн</text>
  <rect x="60" y="150" width="40" height="100" fill="#888"/><rect x="120" y="110" width="40" height="140" fill="#888"/>
  <rect x="180" y="60" width="40" height="190" fill="#888"/></svg>''')
BARS_WITH_VALUE_LABELS = WRAP.format('''<svg data-chart="bar" data-axis-min="0" viewBox="0 0 400 200">
  <rect x="70" y="10" width="300" height="20" fill="#06c"/><text x="376" y="24">1 560</text>
  <rect x="70" y="40" width="190" height="20" fill="#ccc"/><text x="266" y="54">980</text>
  <rect x="70" y="70" width="140" height="20" fill="#ccc"/><text x="216" y="84">720</text>
  <rect x="70" y="100" width="80" height="20" fill="#ccc"/><text x="156" y="114">410</text></svg>''')


class GateTests(unittest.TestCase):
    def errs(self, html, **kw): return ch.check(html, **kw)[0]

    def test_truncated_bar_axis_is_error(self):
        e = self.errs(TRUNCATED_BARS); self.assertTrue(any('не от нуля' in x for x in e), e)

    def test_pie_by_sectors_is_error(self):
        self.assertTrue(any('pie/donut' in x for x in self.errs(PIE_SECTORS)))

    def test_pie_by_conic_gradient_is_error(self):
        self.assertTrue(any('conic-gradient' in x for x in self.errs(PIE_CONIC)))

    def test_donut_by_dasharray_is_error(self):
        self.assertTrue(any('кольцев' in x for x in self.errs(DONUT)))

    def test_3d_is_error(self):
        self.assertTrue(any(x.startswith('3D') for x in self.errs(THREE_D)))

    def test_declared_nonzero_bar_axis_is_error(self):
        self.assertTrue(any('начинается с 5000000' in x for x in self.errs(DECLARED_BAD)))

    def test_dual_axis_is_error(self):
        self.assertTrue(any('двойная ось' in x for x in self.errs(DUAL)))

    def test_warning_text_does_not_excuse(self):
        # ровно случай из отчёта: нечестный график «с предупреждением»
        html = TRUNCATED_BARS.replace('<footer>', '<p>Внимание: ось усечена, это искажает сравнение.</p><footer>')
        self.assertTrue(self.errs(html))

    def test_admitted_truncation_on_line_is_error(self):
        """V-11 (17.11): линия с осью от 5 млн и плашкой «Ось обрезана … рост выглядит сильнее» прошла шлюз."""
        html = WRAP.format('<p><strong>Ось обрезана:</strong> показан диапазон от 5 до 9 млн ₽. Из-за этого рост выглядит сильнее.</p>'
                           '<svg data-chart="line" viewBox="0 0 400 300"><text x="5" y="250">5</text><text x="5" y="50">9</text>'
                           '<polyline points="10,240 390,60" fill="none" stroke="#000"/></svg>')
        e = self.errs(html); self.assertTrue(any('признаёт искажение' in x for x in e), e)

    def test_admission_phrases_are_caught(self):
        for phrase in ('обрезанная ось усиливает впечатление', 'Усечённая ось показывает рост', 'Truncated axis.',
                       'разница высот столбцов визуально преувеличивает рост'):
            html = WRAP.format(f'<p>{phrase}</p><svg data-chart="line" viewBox="0 0 10 10"><path d="M0 0L10 10"/></svg>')
            self.assertTrue(self.errs(html), phrase)

    def test_negated_or_honest_notes_are_not_admissions(self):
        for phrase in ('Ось не обрезана: столбцы начинаются с нуля.', 'Ось столбцов начинается с нуля.',
                       'Линия начинается с 5 млн, шкала отмечена; сравнение величин — в таблице.', 'Без усечённой оси.'):
            html = WRAP.format(f'<p>{phrase}</p><svg data-chart="line" viewBox="0 0 10 10"><path d="M0 0L10 10"/></svg>')
            self.assertEqual([x for x in self.errs(html) if 'признаёт' in x], [], phrase)

    def test_admission_without_chart_is_not_error(self):
        """Текст-объяснение отказа без графика (например, ответ в HTML) не считается нарушением."""
        self.assertEqual(self.errs(WRAP.format('<p>Обрезанная ось сделала бы рост визуально больше, поэтому столбцы от нуля.</p>')), [])

    def test_pie_drawn_by_script_is_error(self):
        """V-11 (17.11, Claude Code): круговая строилась в JS, в разметке только <svg id="pie">."""
        js = ('<svg id="pie" width="320" height="320"></svg><script>const cx=160,cy=160,R=140;let a0=0;'
              '[3,2,1].forEach(v=>{const a1=a0+v;const big=0;'
              'el("path",{d:`M${cx} ${cy} L${cx+R*Math.cos(a0)} ${cy+R*Math.sin(a0)} A${R} ${R} 0 ${big} 1 ${cx+R*Math.cos(a1)} ${cy+R*Math.sin(a1)} Z`});a0=a1;});</script>')
        e = self.errs(WRAP.format(js)); self.assertTrue(any('pie/donut' in x for x in e), e)
        e2 = self.errs(WRAP.format(js.replace('id="pie"', 'id="chart"'))); self.assertTrue(any('скрипт рисует секторы' in x for x in e2), e2)

    def test_strict_zero_catches_truncated_line(self):
        """V-11 (17.11, Claude Code + хук): pie заменён, но линия от 6 млн с пометкой «не с нуля» осталась."""
        line = WRAP.format('<p>Ось Y начинается с 6 млн ₽, не с нуля.</p><svg viewBox="0 0 400 300">'
                           + ''.join(f'<text x="54" y="{300 - i * 40}">{6 + i * 0.5:.1f}</text>' for i in range(7))
                           + '<text x="64" y="320">ноя</text><text x="120" y="320">дек</text><path d="M60 280 L390 30" fill="none"/></svg>')
        self.assertEqual([x for x in self.errs(line) if 'строгий' in x], [], 'без строгого режима линия с отмеченной шкалой допустима')
        e = ch.check(line, strict_zero=True)[0]
        self.assertTrue(any('деления 6' in x for x in e), e); self.assertTrue(any('не с нуля' in x for x in e), e)

    def test_strict_zero_ignores_years_on_x_axis(self):
        line = WRAP.format('<svg viewBox="0 0 400 300">' + ''.join(f'<text x="{40 + i * 60}" y="290">{2010 + i * 2}</text>' for i in range(5))
                           + ''.join(f'<text x="20" y="{260 - i * 60}">{i * 10}</text>' for i in range(4)) + '<path d="M40 250 L380 40"/></svg>')
        self.assertEqual(ch.check(line, strict_zero=True)[0], [])

    def test_honest_bars_pass(self):
        self.assertEqual(self.errs(HONEST_BARS), [])

    def test_value_labels_are_not_mistaken_for_axis(self):
        self.assertEqual(self.errs(BARS_WITH_VALUE_LABELS), [])

    def test_allow_pie_only_with_flag(self):
        self.assertTrue(self.errs(PIE_SECTORS)); self.assertEqual(self.errs(PIE_SECTORS, allow_pie=True), [])

    def test_kit_skeletons_and_golden_pass(self):
        files = [os.path.join(ROOT, '03-skill-template', 'assets', 'dashboard-skeleton.html'),
                 os.path.join(ROOT, '02-references', 'examples', 'acme-dataviz', 'examples', 'dashboard-orders.html')]
        for f in files:
            with open(f, encoding='utf-8') as fh: self.assertEqual(self.errs(fh.read()), [], f)

    def test_charts_declare_their_type_and_zero_axis(self):
        """V-11: скелет и эталон объявляют тип графика, столбцы — ось от нуля; шлюз не предупреждает."""
        files = [os.path.join(ROOT, '03-skill-template', 'assets', 'dashboard-skeleton.html'),
                 os.path.join(ROOT, '02-references', 'examples', 'acme-dataviz', 'assets', 'dashboard-skeleton.html'),
                 os.path.join(ROOT, '02-references', 'examples', 'acme-dataviz', 'examples', 'dashboard-orders.html')]
        for f in files:
            with open(f, encoding='utf-8') as fh: html = fh.read()
            self.assertIn('"data-chart": "line"', html, f)
            self.assertIn('"data-chart": "bar"', html, f)
            self.assertIn('"data-axis-min": "0"', html, f)
            errors, warns = ch.check(html)
            self.assertEqual(errors, [], f)
            self.assertFalse([w for w in warns if 'без объявления типа' in w], f)

    def test_style_skeletons_have_no_errors(self):
        for s in ('yau', 'fragapane', 'bremer', 'lupi', 'nyt'):
            with open(os.path.join(ROOT, '02-references', 'styles', f'{s}.md'), encoding='utf-8') as fh:
                sk = [b for b in re.findall(r'```html\n(.*?)```', fh.read(), re.S) if b.lstrip().startswith('<!DOCTYPE')][-1]
            self.assertEqual(self.errs(sk, allow_complex=True), [], s)

    def test_cli_exit_codes(self):
        d = tempfile.mkdtemp(); bad = os.path.join(d, 'bad.html'); good = os.path.join(d, 'good.html')
        with open(bad, 'w', encoding='utf-8') as fh: fh.write(PIE_SECTORS)
        with open(good, 'w', encoding='utf-8') as fh: fh.write(HONEST_BARS)
        tool = os.path.join(ROOT, 'tools', 'check_honesty.py')
        self.assertEqual(subprocess.run([sys.executable, tool, bad], capture_output=True, text=True).returncode, 1)
        self.assertEqual(subprocess.run([sys.executable, tool, good], capture_output=True, text=True).returncode, 0)
        self.assertEqual(subprocess.run([sys.executable, tool, '/nope.html'], capture_output=True, text=True).returncode, 2)


if __name__ == '__main__':
    unittest.main()
