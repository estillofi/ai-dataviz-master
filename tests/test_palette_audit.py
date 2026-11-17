import importlib.util, os, subprocess, sys, tempfile, unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
spec = importlib.util.spec_from_file_location('palette_audit', os.path.join(ROOT, 'tools', 'palette_audit.py'))
pa = importlib.util.module_from_spec(spec); spec.loader.exec_module(pa)


class ContrastTests(unittest.TestCase):
    def test_black_on_white_is_21(self):
        self.assertAlmostEqual(pa.contrast('#000000', '#FFFFFF'), 21.0, places=1)

    def test_same_color_is_1(self):
        self.assertAlmostEqual(pa.contrast('#336699', '#336699'), 1.0, places=3)

    def test_symmetric(self):
        self.assertAlmostEqual(pa.contrast('#0072B2', '#FFFFFF'), pa.contrast('#FFFFFF', '#0072B2'), places=6)

    def test_short_hex(self):
        self.assertAlmostEqual(pa.contrast('#000', '#fff'), 21.0, places=1)

    def test_known_value(self):
        # #0072B2 на белом: ~5.19:1 (проверено вручную по формуле WCAG)
        self.assertAlmostEqual(pa.contrast('#0072B2', '#FFFFFF'), 5.19, places=1)


class AuditTests(unittest.TestCase):
    def test_low_contrast_text_is_flagged(self):
        report, n = pa.audit({'bg': '#FFFFFF', 'text': ['#A0A0A0'], 'graphics': [], 'categorical': []})
        self.assertGreaterEqual(n, 1)
        self.assertIn('НЕ проходит', report)

    def test_good_text_passes(self):
        _, n = pa.audit({'bg': '#FFFFFF', 'text': ['#1F2933'], 'graphics': [], 'categorical': []})
        self.assertEqual(n, 0)

    def test_red_green_flagged_for_deutan(self):
        report, n = pa.audit({'bg': '#FFFFFF', 'text': [], 'graphics': [], 'categorical': ['#D62728', '#2CA02C']})
        self.assertGreaterEqual(n, 1)
        self.assertIn('дейтан', report)

    def test_blue_orange_not_flagged(self):
        _, n = pa.audit({'bg': '#FFFFFF', 'text': [], 'graphics': [], 'categorical': ['#0072B2', '#D55E00']})
        self.assertEqual(n, 0)

    def test_many_categories_warns(self):
        cats = ['#0072B2', '#D55E00', '#009E73', '#CC79A7', '#E69F00', '#56B4E9', '#000000', '#7A4FB5', '#B34D00']
        report, _ = pa.audit({'bg': '#FFFFFF', 'text': [], 'graphics': [], 'categorical': cats})
        self.assertIn('Больше 6', report)

    def test_cvd_simulation_keeps_gray_gray(self):
        # серый остаётся серым для любого типа дальтонизма
        for m in pa.CVD.values():
            r, g, b = pa.simulate((128, 128, 128), m)
            self.assertLess(max(r, g, b) - min(r, g, b), 12)


class InputAndCountTests(unittest.TestCase):
    """Находки внешнего тестирования F02, F06, F07."""

    def test_low_contrast_category_is_counted(self):
        # F02: оранжевый 2.25:1 и пара красный/зелёный дают ДВА предупреждения, а не одно
        _, n = pa.audit({'bg': '#FFFFFF', 'text': [], 'graphics': [], 'categorical': ['#D62728', '#2CA02C', '#0072B2', '#E69F00']})
        self.assertEqual(n, 2)

    def test_seven_categories_warn(self):
        # F07: набор разрешает до 6 категорий
        cats = ['#0072B2', '#D55E00', '#009E73', '#CC79A7', '#222222', '#7A4FB5', '#B34D00']
        report, n = pa.audit({'bg': '#FFFFFF', 'text': [], 'graphics': [], 'categorical': cats})
        self.assertIn('Больше 6', report)
        self.assertGreaterEqual(n, 1)

    def test_six_categories_ok_count(self):
        cats = ['#0072B2', '#D55E00', '#009E73', '#CC79A7', '#222222', '#7A4FB5']
        report, _ = pa.audit({'bg': '#FFFFFF', 'text': [], 'graphics': [], 'categorical': cats})
        self.assertNotIn('Больше 6', report)

    def test_bad_hex_raises_clear_error(self):
        # F06: вместо traceback понятная ошибка
        with self.assertRaises(pa.ColorError):
            pa.audit({'bg': 'red', 'text': ['#000000'], 'graphics': [], 'categorical': []})

    def test_cli_bad_hex_exit_code_2_no_traceback(self):
        r = subprocess.run([sys.executable, os.path.join(ROOT, 'tools', 'palette_audit.py'), '--bg', 'red', '--categorical', '#0072B2'],
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 2)
        self.assertNotIn('Traceback', r.stderr)
        self.assertIn('HEX', r.stderr)

    def test_empty_palette_is_error_not_zero_warnings(self):
        with self.assertRaises(pa.ColorError):
            pa.audit({'bg': '#FFFFFF', 'text': [], 'graphics': [], 'categorical': []})

    def test_cli_empty_exit_code_2(self):
        r = subprocess.run([sys.executable, os.path.join(ROOT, 'tools', 'palette_audit.py'), '--bg', '#FFFFFF'], capture_output=True, text=True)
        self.assertEqual(r.returncode, 2)

    def test_cli_missing_json_exit_2_no_traceback(self):
        r = subprocess.run([sys.executable, os.path.join(ROOT, 'tools', 'palette_audit.py'), '--json', '/nope/palette.json'], capture_output=True, text=True)
        self.assertEqual(r.returncode, 2)
        self.assertNotIn('Traceback', r.stderr)
        self.assertIn('/nope/palette.json', r.stderr)

    def test_cli_invalid_json_exit_2_no_traceback(self):
        d = tempfile.mkdtemp(); p = os.path.join(d, 'bad.json')
        with open(p, 'w', encoding='utf-8') as fh: fh.write('{bg: ')
        r = subprocess.run([sys.executable, os.path.join(ROOT, 'tools', 'palette_audit.py'), '--json', p], capture_output=True, text=True)
        self.assertEqual(r.returncode, 2)
        self.assertNotIn('Traceback', r.stderr)
        self.assertIn(p, r.stderr)


if __name__ == '__main__':
    unittest.main()
