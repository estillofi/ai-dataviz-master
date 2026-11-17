import os, subprocess, sys, tempfile, unittest, zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PY = sys.executable
ACME = os.path.join(ROOT, '02-references', 'examples', 'acme-dataviz')


def run(*a): return subprocess.run([PY, *a], cwd=ROOT, capture_output=True, text=True)


def write(d, name, text):
    p = os.path.join(d, name)
    with open(p, 'w', encoding='utf-8') as fh: fh.write(text)
    return p


class CheckTokensTests(unittest.TestCase):
    def test_golden_example_uses_only_tokens(self):
        r = run('tools/check_tokens.py', os.path.join(ACME, 'examples', 'dashboard-orders.html'), os.path.join(ACME, 'assets', 'tokens.css'))
        self.assertEqual(r.returncode, 0, r.stdout)

    def test_foreign_color_and_font_flagged(self):
        d = tempfile.mkdtemp()
        css = write(d, 't.css', ':root{--accent:#C2620A;--ink:#1B2A41;--font:"Inter",Arial,sans-serif;}')
        html = write(d, 'a.html', '<style>:root{--accent:#C2620A;--ink:#1B2A41}.x{color:#FF00FF;font-family:"Comic Sans MS"}.y{color:var(--ink)}</style>')
        r = run('tools/check_tokens.py', html, css)
        self.assertEqual(r.returncode, 1)
        self.assertIn('#ff00ff', r.stdout); self.assertIn('comic sans ms', r.stdout)

    def test_token_drift_flagged(self):
        d = tempfile.mkdtemp()
        css = write(d, 't.css', ':root{--accent:#C2620A;--font:Inter;}')
        html = write(d, 'a.html', '<style>:root{--accent:#123456}.x{color:var(--accent)}</style>')
        r = run('tools/check_tokens.py', html, css)
        self.assertEqual(r.returncode, 1); self.assertIn('РАСХОЖДЕНИЕ', r.stdout)

    def test_white_and_short_hex_allowed(self):
        d = tempfile.mkdtemp()
        css = write(d, 't.css', ':root{--accent:#C2620A;--font:Inter;}')
        html = write(d, 'a.html', '<style>.x{color:#fff;background:#C2620A;border-color:#c2620a}</style>')
        self.assertEqual(run('tools/check_tokens.py', html, css).returncode, 0)

    def test_foreign_variable_with_color_is_flagged(self):
        d = tempfile.mkdtemp()
        css = write(d, 't.css', ':root{--accent:#C2620A;}')
        html = write(d, 'a.html', '<style>:root{--foreign:#ff00ff}.bar{color:var(--foreign)}</style>')
        r = run('tools/check_tokens.py', html, css)
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn('--foreign', r.stdout)

    def test_foreign_variable_with_font_is_flagged(self):
        d = tempfile.mkdtemp()
        css = write(d, 't.css', ':root{--accent:#C2620A;--font:Inter;}')
        html = write(d, 'a.html', '<style>:root{--my-font:"Comic Sans MS",sans-serif}.x{font-family:var(--my-font)}</style>')
        r = run('tools/check_tokens.py', html, css)
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn('--my-font', r.stdout)

    def test_var_from_tokens_is_resolved(self):
        d = tempfile.mkdtemp()
        css = write(d, 't.css', ':root{--accent:#C2620A;--font:Inter;}')
        html = write(d, 'a.html', '<style>.x{color:var(--accent);font-family:var(--font)}</style>')
        self.assertEqual(run('tools/check_tokens.py', html, css).returncode, 0)

    def test_missing_file_exit_2(self):
        self.assertEqual(run('tools/check_tokens.py', '/nope.html', '/nope.css').returncode, 2)

    def test_non_utf8_file_exit_2_no_traceback(self):
        d = tempfile.mkdtemp()
        css = write(d, 't.css', ':root{--accent:#C2620A;}')
        p = os.path.join(d, 'a.html')
        with open(p, 'wb') as fh: fh.write('<style>.x{color:#C2620A}</style>привет'.encode('cp1251'))
        r = run('tools/check_tokens.py', p, css)
        self.assertEqual(r.returncode, 2)
        self.assertNotIn('Traceback', r.stderr)

    def make_pptx(self, path, hexes):
        runs = ''.join(f'<a:solidFill><a:srgbClr val="{h}"/></a:solidFill>' for h in hexes)
        with zipfile.ZipFile(path, 'w') as z:
            z.writestr('[Content_Types].xml', '<?xml version="1.0"?><Types/>')
            z.writestr('ppt/slides/slide1.xml', f'<?xml version="1.0"?><p:sld xmlns:a="a"><a:rPr>{runs}</a:rPr></p:sld>')
            z.writestr('ppt/theme/theme1.xml', '<?xml version="1.0"?><a:theme xmlns:a="a"><a:clrScheme/></a:theme>')

    def test_pptx_color_outside_tokens_is_flagged(self):
        """V-12: цвета слайдов проверяются по токенам."""
        d = tempfile.mkdtemp()
        css = write(d, 't.css', ':root{--accent:#C2620A;}')
        p = os.path.join(d, 'deck.pptx'); self.make_pptx(p, ['C2620A', 'FF00FF'])
        r = run('tools/check_tokens.py', p, css)
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn('#ff00ff', r.stdout)

    def test_pptx_tokens_only_passes(self):
        d = tempfile.mkdtemp()
        css = write(d, 't.css', ':root{--accent:#C2620A;}')
        p = os.path.join(d, 'deck.pptx'); self.make_pptx(p, ['C2620A'])
        self.assertEqual(run('tools/check_tokens.py', p, css).returncode, 0)


class CompareOutputsTests(unittest.TestCase):
    def test_noise_is_ignored(self):
        d = tempfile.mkdtemp()
        a = write(d, 'a.html', '<html>\n<!-- gen 1 -->\n<p>Привет</p>\n<span data-volatile>12:00</span>\n</html>\n')
        b = write(d, 'b.html', '<html>\r\n   <p>Привет</p>   \r\n<span data-volatile>12:05</span>\r\n<!-- gen 2 --></html>')
        r = run('tools/compare_outputs.py', a, b)
        self.assertEqual(r.returncode, 0, r.stdout)

    def test_real_difference_detected(self):
        d = tempfile.mkdtemp()
        a = write(d, 'a.html', '<p style="color:#111">1</p>')
        b = write(d, 'b.html', '<p style="color:#222">1</p>')
        r = run('tools/compare_outputs.py', a, b, '--show-diff')
        self.assertEqual(r.returncode, 1); self.assertIn('#222', r.stdout)

    def test_random_id_is_a_difference_not_noise(self):
        d = tempfile.mkdtemp()
        a = write(d, 'a.html', '<g id="c-48213"></g>'); b = write(d, 'b.html', '<g id="c-77102"></g>')
        self.assertEqual(run('tools/compare_outputs.py', a, b).returncode, 1)

    def test_spaces_inside_script_string_are_significant(self):
        d = tempfile.mkdtemp()
        a = write(d, 'a.html', '<p>x</p><script>const x = "a  b";</script>')
        b = write(d, 'b.html', '<p>x</p><script>const x = "a b";</script>')
        self.assertEqual(run('tools/compare_outputs.py', a, b).returncode, 1)

    def test_spaces_inside_attribute_value_are_significant(self):
        d = tempfile.mkdtemp()
        a = write(d, 'a.html', '<p class="a  b">x</p>')
        b = write(d, 'b.html', '<p class="a b">x</p>')
        self.assertEqual(run('tools/compare_outputs.py', a, b).returncode, 1)

    def test_spaces_inside_pre_are_significant(self):
        d = tempfile.mkdtemp()
        a = write(d, 'a.html', '<pre>a  b</pre>')
        b = write(d, 'b.html', '<pre>a b</pre>')
        self.assertEqual(run('tools/compare_outputs.py', a, b).returncode, 1)

    def test_indentation_noise_still_ignored(self):
        d = tempfile.mkdtemp()
        a = write(d, 'a.html', '<div>\n  <p>x</p>\n</div>')
        b = write(d, 'b.html', '<div>\r\n<p>x</p>\r\n</div>')
        self.assertEqual(run('tools/compare_outputs.py', a, b).returncode, 0)

    def test_missing_file_exit_2(self):
        self.assertEqual(run('tools/compare_outputs.py', '/nope1', '/nope2').returncode, 2)

    def test_non_utf8_file_exit_2_no_traceback(self):
        d = tempfile.mkdtemp()
        a = write(d, 'a.html', '<p>x</p>')
        b = os.path.join(d, 'b.html')
        with open(b, 'wb') as fh: fh.write('<p>привет</p>'.encode('cp1251'))
        r = run('tools/compare_outputs.py', a, b)
        self.assertEqual(r.returncode, 2)
        self.assertNotIn('Traceback', r.stderr)


if __name__ == '__main__':
    unittest.main()
