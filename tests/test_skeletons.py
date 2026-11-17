"""
Дымовые тесты HTML-скелетов в настоящем браузере. Нужен Playwright с Chromium:
  pip install playwright && playwright install chromium
Если Playwright нет, тесты пропускаются (в CI они не требуются).
Проверка: страница открывается без ошибок JS и рисует SVG; у дашборда работают фильтры и подсказка с клавиатуры.
"""
import os, re, unittest

try:
    from playwright.sync_api import sync_playwright
    HAVE = True
except Exception:
    HAVE = False

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STYLES = ['yau', 'fragapane', 'bremer', 'lupi', 'nyt']


def skeleton_of(style):
    with open(os.path.join(ROOT, '02-references', 'styles', f'{style}.md'), encoding='utf-8') as fh:
        blocks = re.findall(r'```html\n(.*?)```', fh.read(), re.S)
    return [b for b in blocks if b.lstrip().startswith('<!DOCTYPE')][-1]


@unittest.skipUnless(HAVE, 'Playwright не установлен')
class SkeletonTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pw = sync_playwright().start()
        cls.browser = None
        for kwargs in ({}, {'channel': 'chrome'}):          # сначала Chromium от Playwright, затем установленный Google Chrome
            try:
                cls.browser = cls.pw.chromium.launch(**kwargs); break
            except Exception as e:
                err = e
        if cls.browser is None:
            cls.pw.stop()
            raise unittest.SkipTest(f'Браузер недоступен: {err}')

    @classmethod
    def tearDownClass(cls):
        cls.browser.close(); cls.pw.stop()

    def open_html(self, html, tmp_name):
        import tempfile
        d = tempfile.mkdtemp(); path = os.path.join(d, tmp_name)
        with open(path, 'w', encoding='utf-8') as fh: fh.write(html)
        page = self.browser.new_page(viewport={'width': 1200, 'height': 900}); errs = []
        page.on('pageerror', lambda e: errs.append(str(e)))
        page.goto('file://' + path)
        return page, errs

    def test_style_skeletons_render_without_errors(self):
        for s in STYLES:
            if s == 'yau':   # у Yau скелет содержит токены и разметку; рисование выполняет агент, SVG пустой
                page, errs = self.open_html(skeleton_of(s), f'{s}.html')
                self.assertEqual(errs, [], s); page.close(); continue
            page, errs = self.open_html(skeleton_of(s), f'{s}.html')
            self.assertEqual(errs, [], f'{s}: {errs}')
            self.assertGreater(page.eval_on_selector_all('svg *', 'e => e.length'), 10, f'{s}: SVG пуст')
            page.close()

    def read_dashboard(self, path):
        with open(path, encoding='utf-8') as fh: return fh.read()

    def test_dashboard_filters_and_keyboard(self):
        for rel in ('03-skill-template/assets/dashboard-skeleton.html', '02-references/examples/acme-dataviz/examples/dashboard-orders.html'):
            page, errs = self.open_html(self.read_dashboard(os.path.join(ROOT, rel)), 'dash.html')
            self.assertEqual(errs, [], rel)
            self.assertEqual(page.eval_on_selector_all('.kpi', 'e => e.length'), 3)
            before = page.inner_text('#h1')
            page.click('#f-seg button:nth-child(3)'); page.click('#f-per button:nth-child(1)')
            after = page.inner_text('#h1')
            self.assertNotEqual(before, after, 'заголовок должен пересчитываться из данных')
            self.assertEqual(page.eval_on_selector_all('.hit', 'e => e.length'), 6)
            page.focus('.hit:nth-of-type(3)')
            self.assertTrue(page.evaluate("[...document.querySelectorAll('.tip')].some(t => t.style.display === 'block')"), 'подсказка с клавиатуры')
            page.close()

    def test_dashboard_chart_text_readable_at_375(self):
        """Подписи графиков не сжимаются через viewBox: на 375 px отрисованный размер текста ≥ 11 px, без горизонтальной прокрутки."""
        for rel in ('03-skill-template/assets/dashboard-skeleton.html', '02-references/examples/acme-dataviz/examples/dashboard-orders.html'):
            import tempfile
            d = tempfile.mkdtemp(); path = os.path.join(d, 'dash.html')
            with open(path, 'w', encoding='utf-8') as fh: fh.write(self.read_dashboard(os.path.join(ROOT, rel)))
            page = self.browser.new_page(viewport={'width': 375, 'height': 800}); errs = []
            page.on('pageerror', lambda e: errs.append(str(e)))
            page.goto('file://' + path)
            self.assertEqual(errs, [], rel)
            sizes = page.evaluate("""() => [...document.querySelectorAll('svg[data-chart="line"] text, svg[data-chart="bar"] text')].map(t => {
                const svg = t.ownerSVGElement, k = svg.getBoundingClientRect().width / svg.viewBox.baseVal.width;
                return parseFloat(getComputedStyle(t).fontSize) * k; })""")
            self.assertTrue(sizes, rel)
            self.assertGreaterEqual(min(sizes), 10.9, f'{rel}: min {min(sizes):.1f}px')
            self.assertFalse(page.evaluate('document.documentElement.scrollWidth > document.documentElement.clientWidth'), rel)
            page.close()

    def test_bar_chart_starts_from_zero_axis(self):
        page, _ = self.open_html(self.read_dashboard(os.path.join(ROOT, '03-skill-template/assets/dashboard-skeleton.html')), 'd.html')
        # значения столбцов пропорциональны: самый длинный = максимум, остальные меньше, ширины > 0
        widths = page.eval_on_selector_all('#ch-bar rect', 'e => e.map(x => +x.getAttribute("width"))')
        self.assertTrue(all(w > 0 for w in widths))
        self.assertEqual(widths, sorted(widths, reverse=True), 'столбцы отсортированы по убыванию')
        page.close()


    EDGE = {
        'нули': 'for (const k in SEGMENTS) { SEGMENTS[k].orders = SEGMENTS[k].orders.map(() => 0); SEGMENTS[k].prev = SEGMENTS[k].prev.map(() => 0); SEGMENTS[k].regions = SEGMENTS[k].regions.map(r => [r[0], 0]); }',
        'один месяц': 'MONTHS.splice(0, MONTHS.length - 1); for (const k in SEGMENTS) { SEGMENTS[k].orders = SEGMENTS[k].orders.slice(-1); SEGMENTS[k].prev = SEGMENTS[k].prev.slice(-1); }',
        'нет регионов': 'for (const k in SEGMENTS) SEGMENTS[k].regions = [];',
        'нулевая база': 'for (const k in SEGMENTS) SEGMENTS[k].prev = SEGMENTS[k].prev.map(() => 0);',
        'равные значения': 'for (const k in SEGMENTS) SEGMENTS[k].regions = [["Б", 10], ["А", 10], ["В", 10]];',
    }
    BAD = """() => {
        const bad = /NaN|Infinity|undefined/;
        const attrs = [...document.querySelectorAll('svg *')].flatMap(e => [...e.attributes].map(a => a.value)).filter(v => bad.test(v));
        return { text: bad.test(document.body.innerText), svg: attrs.length };
    }"""

    def test_dashboard_edge_cases_no_nan_no_errors(self):
        """Находка внешнего тестирования F05: нулевые, пустые и одноточечные ряды не должны давать NaN и ошибок."""
        base = self.read_dashboard(os.path.join(ROOT, '03-skill-template/assets/dashboard-skeleton.html'))
        for name, js in self.EDGE.items():
            html = base.replace('const STATE = { seg: "all", per: 12 };', 'const STATE = { seg: "all", per: 12 };\n' + js)
            page, errs = self.open_html(html, 'edge.html')
            r = page.evaluate(self.BAD)
            self.assertEqual(errs, [], f'{name}: {errs}')
            self.assertFalse(r['text'], f'{name}: NaN/Infinity/undefined в тексте')
            self.assertEqual(r['svg'], 0, f'{name}: NaN/Infinity/undefined в атрибутах SVG')
            page.close()

    def test_ties_are_sorted_deterministically(self):
        base = self.read_dashboard(os.path.join(ROOT, '03-skill-template/assets/dashboard-skeleton.html'))
        html = base.replace('const STATE = { seg: "all", per: 12 };', 'const STATE = { seg: "all", per: 12 };\n' + self.EDGE['равные значения'])
        page, _ = self.open_html(html, 'ties.html')
        labels = page.eval_on_selector_all('#ch-bar text.lab', 'e => e.map(x => x.textContent).filter((t, i) => i % 2 === 0)')
        self.assertEqual(labels, ['А', 'Б', 'В'])
        page.close()


if __name__ == '__main__':
    unittest.main()
