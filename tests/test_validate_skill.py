import importlib.util, os, shutil, subprocess, sys, tempfile, unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
spec = importlib.util.spec_from_file_location('validate_skill', os.path.join(ROOT, 'tools', 'validate_skill.py'))
vs = importlib.util.module_from_spec(spec); spec.loader.exec_module(vs)


def make_skill(tmp, name, frontmatter, body='# Тест\n\nТело.\n'):
    d = os.path.join(tmp, name); os.makedirs(d)
    with open(os.path.join(d, 'SKILL.md'), 'w', encoding='utf-8') as fh:
        fh.write(frontmatter + body)
    return d


GOOD = '---\nname: demo-dataviz\ndescription: "Графики и дашборды, а также слайды с данными. Используй всегда."\n---\n'


class ValidateTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_example_skill_is_valid(self):
        errs, _ = vs.validate(os.path.join(ROOT, '02-references', 'examples', 'acme-dataviz'))
        self.assertEqual(errs, [])

    def test_missing_honesty_gate_warns(self):
        """V-11: раздел 0 ссылается на шлюз; скилл без check_honesty.py — предупреждение (в строгом режиме FAIL)."""
        _, warns = vs.validate(make_skill(self.tmp, 'demo-dataviz', GOOD))
        self.assertTrue(any('нет шлюза честности' in w for w in warns), warns)

    def test_gate_in_scripts_is_accepted(self):
        d = make_skill(self.tmp, 'demo-dataviz', GOOD, body='Запусти `scripts/check_honesty.py`.\n')
        os.makedirs(os.path.join(d, 'scripts')); open(os.path.join(d, 'scripts', 'check_honesty.py'), 'w').close()
        errs, warns = vs.validate(d)
        self.assertEqual(errs, []); self.assertFalse(any('шлюза' in w for w in warns), warns)

    def test_missing_referenced_tool_is_error(self):
        errs, _ = vs.validate(make_skill(self.tmp, 'demo-dataviz', GOOD, body='Запусти `tools/check_honesty.py`.\n'))
        self.assertTrue(any('tools/check_honesty.py' in e for e in errs), errs)

    def test_acme_gate_is_verbatim_copy(self):
        with open(os.path.join(ROOT, 'tools', 'check_honesty.py'), 'rb') as a, \
             open(os.path.join(ROOT, '02-references', 'examples', 'acme-dataviz', 'tools', 'check_honesty.py'), 'rb') as b:
            self.assertEqual(a.read(), b.read(), 'копия шлюза в примере Acme устарела')

    def test_good_skill_passes(self):
        errs, _ = vs.validate(make_skill(self.tmp, 'demo-dataviz', GOOD))
        self.assertEqual(errs, [])

    def test_unquoted_colon_is_error(self):
        fm = '---\nname: demo-dataviz\ndescription: Делает графики. Результат: один HTML и слайды\n---\n'
        errs, _ = vs.validate(make_skill(self.tmp, 'demo-dataviz', fm))
        self.assertTrue(any("не взято в кавычки" in e for e in errs))

    def test_name_must_match_folder(self):
        errs, _ = vs.validate(make_skill(self.tmp, 'other-dir', GOOD))
        self.assertTrue(any('не равен имени папки' in e for e in errs))

    def test_uppercase_name_is_error(self):
        fm = '---\nname: Demo_DataViz\ndescription: "графики и слайды"\n---\n'
        errs, _ = vs.validate(make_skill(self.tmp, 'Demo_DataViz', fm))
        self.assertTrue(any('допустимы строчные' in e for e in errs))

    def test_description_too_long(self):
        fm = '---\nname: demo-dataviz\ndescription: "' + 'график ' * 200 + '"\n---\n'
        errs, _ = vs.validate(make_skill(self.tmp, 'demo-dataviz', fm))
        self.assertTrue(any('длиннее 1024' in e for e in errs))

    def test_missing_frontmatter(self):
        errs, _ = vs.validate(make_skill(self.tmp, 'demo-dataviz', ''))
        self.assertTrue(errs)

    def test_missing_referenced_file(self):
        errs, _ = vs.validate(make_skill(self.tmp, 'demo-dataviz', GOOD, '# T\n\nЧитай `references/nope.md`.\n'))
        self.assertTrue(any('не найден' in e for e in errs))

    def test_placeholder_left(self):
        errs, _ = vs.validate(make_skill(self.tmp, 'demo-dataviz', GOOD, '# T {{КОМАНДА}}\n'))
        self.assertTrue(any('заготовки' in e for e in errs))

    def test_no_presentation_words_warns(self):
        fm = '---\nname: demo-dataviz\ndescription: "Делает графики и дашборды."\n---\n'
        _, warns = vs.validate(make_skill(self.tmp, 'demo-dataviz', fm))
        self.assertTrue(any('презентац' in w for w in warns))


class StubDetectionTests(unittest.TestCase):
    """Находка внешнего тестирования: валидатор пропускал пустые эталоны и скелет-заглушку."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def cli(self, path, strict=False):
        args = [sys.executable, os.path.join(ROOT, 'tools', 'validate_skill.py')] + (['--strict'] if strict else []) + [path]
        return subprocess.run(args, capture_output=True, text=True)

    def test_empty_examples_warns_and_strict_fails(self):
        d = make_skill(self.tmp, 'demo-dataviz', GOOD); os.makedirs(os.path.join(d, 'examples'))
        _, warns = vs.validate(d)
        self.assertTrue(any('нет эталонов' in w for w in warns))
        self.assertEqual(self.cli(d).returncode, 0)
        self.assertEqual(self.cli(d, strict=True).returncode, 1)

    def test_stub_skeleton_warns(self):
        d = make_skill(self.tmp, 'demo-dataviz', GOOD); os.makedirs(os.path.join(d, 'assets'))
        with open(os.path.join(d, 'assets', 'dashboard-skeleton.html'), 'w', encoding='utf-8') as fh: fh.write('<html>заглушка</html>')
        _, warns = vs.validate(d)
        self.assertTrue(any('заглушк' in w for w in warns))

    def test_no_evals_warns(self):
        _, warns = vs.validate(make_skill(self.tmp, 'demo-dataviz', GOOD))
        self.assertTrue(any('evals' in w for w in warns))

    def test_example_passes_strict(self):
        r = self.cli(os.path.join(ROOT, '02-references', 'examples', 'acme-dataviz'), strict=True)
        self.assertEqual(r.returncode, 0, r.stdout)

    def test_cyrillic_path(self):
        d = os.path.join(self.tmp, 'кириллица'); os.makedirs(d)
        shutil.copytree(os.path.join(ROOT, '02-references', 'examples', 'acme-dataviz'), os.path.join(d, 'acme-dataviz'))
        errs, _ = vs.validate(os.path.join(d, 'acme-dataviz'))
        self.assertEqual(errs, [])

    def test_non_utf8_skill_md_exit_2_no_traceback(self):
        d = make_skill(self.tmp, 'demo-dataviz', GOOD)
        with open(os.path.join(d, 'SKILL.md'), 'wb') as fh:
            fh.write('---\nname: demo-dataviz\n---\n# Привет\n'.encode('cp1251'))
        r = self.cli(d)
        self.assertEqual(r.returncode, 2, r.stdout + r.stderr)
        self.assertNotIn('Traceback', r.stderr)
        self.assertIn('SKILL.md', r.stderr)


if __name__ == '__main__':
    unittest.main()
