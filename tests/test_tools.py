import os, shutil, subprocess, sys, tempfile, unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PY = sys.executable
EXAMPLE = os.path.join(ROOT, '02-references', 'examples', 'acme-dataviz')


def run(*args, cwd=ROOT):
    return subprocess.run([PY, *args], cwd=cwd, capture_output=True, text=True)


class InstallTests(unittest.TestCase):
    def setUp(self):
        self.home = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.home, ignore_errors=True)

    def test_installs_for_both_agents(self):
        r = run('tools/install_skill.py', EXAMPLE, '--home', self.home)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertTrue(os.path.isfile(os.path.join(self.home, '.claude', 'skills', 'acme-dataviz', 'SKILL.md')))
        self.assertTrue(os.path.isfile(os.path.join(self.home, '.agents', 'skills', 'acme-dataviz', 'SKILL.md')))

    def test_does_not_overwrite_without_force(self):
        run('tools/install_skill.py', EXAMPLE, '--home', self.home)
        r = run('tools/install_skill.py', EXAMPLE, '--home', self.home)
        self.assertIn('уже существует', r.stdout)

    def test_dry_run_changes_nothing(self):
        r = run('tools/install_skill.py', EXAMPLE, '--home', self.home, '--dry-run')
        self.assertEqual(r.returncode, 0)
        self.assertFalse(os.path.exists(os.path.join(self.home, '.agents')))

    def test_refuses_invalid_skill(self):
        bad = tempfile.mkdtemp(); d = os.path.join(bad, 'bad-skill'); os.makedirs(d)
        with open(os.path.join(d, 'SKILL.md'), 'w', encoding='utf-8') as fh:
            fh.write('без frontmatter')
        r = run('tools/install_skill.py', d, '--home', self.home)
        self.assertEqual(r.returncode, 1)
        self.assertFalse(os.path.exists(os.path.join(self.home, '.agents')))
        shutil.rmtree(bad, ignore_errors=True)

    def test_repo_scope(self):
        repo = tempfile.mkdtemp()
        r = run('tools/install_skill.py', EXAMPLE, '--scope', 'repo', '--repo', repo, '--target', 'codex')
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertTrue(os.path.isfile(os.path.join(repo, '.agents', 'skills', 'acme-dataviz', 'SKILL.md')))
        shutil.rmtree(repo, ignore_errors=True)


class BundleTests(unittest.TestCase):
    """Находка внешнего тестирования F04: единый документ не должен ссылаться на файлы, которых в нём нет, молча."""

    def build(self, *args):
        out = os.path.join(tempfile.mkdtemp(), 'bundle.md')
        r = run('tools/bundle_single_file.py', '--out', out, *args)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        with open(out, encoding='utf-8') as fh: return fh.read()

    def test_default_has_recommended_styles_and_required_files(self):
        t = self.build()
        for marker in ('=== FILE: README.md ===', '=== FILE: AGENTS.md ===', '01-integrity-and-perception.md',
                       '=== FILE: 02-references/styles/yau.md ===', '=== FILE: 02-references/styles/nyt.md ===',
                       '=== FILE: 00-session/state.template.md ===', '=== FILE: 01-brand-inputs/README.md ===',
                       '=== FILE: 01-brand-inputs/intake-form.md ===', 'dashboard-skeleton.html', 'Режим «только чат»'):
            self.assertIn(marker, t, marker)
        self.assertNotIn('=== FILE: 02-references/styles/bremer.md ===', t)

    def test_missing_styles_are_declared_in_preface(self):
        t = self.build()
        head = t[:t.index('=== FILE: README.md ===')]
        for s in ('fragapane', 'bremer', 'lupi'): self.assertIn(f'`{s}`', head)
        self.assertNotIn('`yau`', head)

    def test_all_styles(self):
        t = self.build('--styles', 'all')
        for s in ('yau', 'fragapane', 'bremer', 'lupi', 'nyt'):
            self.assertIn(f'=== FILE: 02-references/styles/{s}.md ===', t)
        self.assertNotIn('файлов стилей:', t[:t.index('=== FILE: README.md ===')])

    def test_none_styles(self):
        t = self.build('--styles', 'none')
        self.assertNotIn('=== FILE: 02-references/styles/yau.md ===', t)
        self.assertIn('файлов стилей:', t[:t.index('=== FILE: README.md ===')])

    def test_unknown_style_rejected(self):
        r = run('tools/bundle_single_file.py', '--styles', 'picasso', '--out', os.path.join(tempfile.mkdtemp(), 'x.md'))
        self.assertNotEqual(r.returncode, 0)

    def test_every_referenced_core_and_template_file_is_inside_bundle(self):
        """Любой путь `02-references/core-rules/...` и `03-skill-template/...`, упомянутый в AGENTS.md, есть в документе."""
        import re
        t = self.build()
        with open(os.path.join(ROOT, 'AGENTS.md'), encoding='utf-8') as fh: a = fh.read()
        refs = set(re.findall(r'`((?:02-references/core-rules|03-skill-template|01-brand-inputs|00-session)/[\w\-./]+\.(?:md|html|css))`', a))
        refs = {r for r in refs if '*' not in r and '<' not in r and r != '00-session/state.md'}   # state.md создаёт агент, в набор он не входит
        missing = sorted(r for r in refs if f'=== FILE: {r} ===' not in t)
        self.assertEqual(missing, [], f'в документе нет файлов, на которые ссылается AGENTS.md: {missing}')


class LintTests(unittest.TestCase):
    def test_repo_passes_lint(self):
        r = run('tests/lint_kit.py')
        self.assertEqual(r.returncode, 0, r.stdout)

    def test_lint_catches_broken_link_and_forbidden_term(self):
        tmp = tempfile.mkdtemp(); dst = os.path.join(tmp, 'repo')
        shutil.copytree(ROOT, dst, ignore=shutil.ignore_patterns('.git', 'dist', '__pycache__'))
        with open(os.path.join(dst, 'README.md'), 'a', encoding='utf-8') as f:
            f.write('\nСмотри `02-references/core-rules/99-nope.md` и Корифей.\n')
        r = run('tests/lint_kit.py', cwd=dst)
        self.assertEqual(r.returncode, 1)
        self.assertIn('99-nope.md', r.stdout)
        self.assertIn('Корифей', r.stdout)
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == '__main__':
    unittest.main()
