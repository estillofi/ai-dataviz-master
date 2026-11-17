import glob, os, re, subprocess, sys, tempfile, unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PY = sys.executable
KEY_WORDS = ['Правильное поведение', 'Критерии успеха', 'внедр', 'poisoned', 'ловушк', 'R18', 'tests/fixtures']


def prep(persona, work, *extra):
    return subprocess.run([PY, os.path.join(ROOT, 'tests', 'run_persona.py'), '--persona', str(persona), '--prepare-only', '--workdir', work, *extra],
                          capture_output=True, text=True)


def sandboxes(work, persona):
    return sorted(glob.glob(os.path.join(work, f'dvm-run-{persona}-*')))


def one_sandbox(work, persona):
    dirs = sandboxes(work, persona)
    assert len(dirs) == 1, dirs
    return dirs[0]


class RunPersonaTests(unittest.TestCase):
    def test_sandbox_has_no_tests_dir_and_no_key(self):
        for n in (1, 2, 3):
            work = tempfile.mkdtemp(); r = prep(n, work); self.assertEqual(r.returncode, 0, r.stderr)
            sb = one_sandbox(work, n)
            self.assertFalse(os.path.exists(os.path.join(sb, 'tests')), 'в песочнице не должно быть tests/ (там ключ проверки)')
            for rel in ('AGENTS.md', '02-references/core-rules/01-integrity-and-perception.md', '03-skill-template/SKILL.template.md'):
                self.assertTrue(os.path.isfile(os.path.join(sb, rel)), rel)
            # в песочнице нигде нет файлов ключа
            for r_, _, fs in os.walk(sb):
                for f in fs:
                    self.assertNotIn('persona-', f); self.assertNotIn('CODEX-TESTER', f)

    def test_prompt_has_owner_script_but_no_key(self):
        for n in (1, 2, 3):
            work = tempfile.mkdtemp(); prep(n, work)
            prompts = glob.glob(os.path.join(work, f'dvm-prompt-{n}-*.txt'))
            self.assertEqual(len(prompts), 1, prompts)
            with open(prompts[0], encoding='utf-8') as fh: p = fh.read()
            self.assertIn('=== СЦЕНАРИЙ ВЛАДЕЛЬЦА ===', p); self.assertIn('Твои ответы по этапам', p)
            for kw in KEY_WORDS: self.assertNotIn(kw.lower(), p.lower(), f'утечка ключа в запрос: {kw}')

    def test_materials_are_placed_under_neutral_names(self):
        work = tempfile.mkdtemp(); prep(2, work); sb = one_sandbox(work, 2)
        for rel in ('01-brand-inputs/assets/design-system/partner-brandbook.md', '01-brand-inputs/assets/palette/palette.json',
                    '01-brand-inputs/assets/sample-data/sales_monthly.csv', '01-brand-inputs/assets/logo/logo.svg'):
            self.assertTrue(os.path.isfile(os.path.join(sb, rel)), rel)
        with open(os.path.join(sb, '01-brand-inputs/assets/design-system/partner-brandbook.md'), encoding='utf-8') as fh:
            self.assertIn('example.com', fh.read())          # ловушка на месте

    def test_baseline_is_created_and_clean_sandbox_fails_check(self):
        work = tempfile.mkdtemp(); prep(1, work)
        bases = glob.glob(os.path.join(work, 'dvm-base-1-*.json'))
        self.assertEqual(len(bases), 1, bases)
        sb = one_sandbox(work, 1)
        r = subprocess.run([PY, os.path.join(ROOT, 'tests', 'check_run.py'), 'check', sb, '--baseline', bases[0], '--persona', '1'],
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 1, 'если агент ничего не сделал, проверка должна падать')

    def test_two_prepare_only_create_two_distinct_sandboxes(self):
        """V-04: второй прогон не должен молча удалять первую песочницу."""
        work = tempfile.mkdtemp()
        self.assertEqual(prep(1, work).returncode, 0)
        first = one_sandbox(work, 1)
        self.assertEqual(prep(1, work).returncode, 0)
        dirs = sandboxes(work, 1)
        self.assertEqual(len(dirs), 2, dirs)
        self.assertTrue(os.path.isdir(first), 'первая песочница удалена')
        self.assertEqual(first, dirs[0])
        self.assertNotEqual(dirs[0], dirs[1])

    def test_prepare_only_prints_network_policy(self):
        """V-09: прогон по умолчанию без сети; в выводе должна быть строка про сеть."""
        work = tempfile.mkdtemp()
        r = prep(1, work)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn('Сеть:', r.stdout)

    def test_prepare_only_codex_command_has_default_flags(self):
        """Песочница не Git-репозиторий: команда codex должна включать --skip-git-repo-check и --sandbox workspace-write, но не полный доступ."""
        work = tempfile.mkdtemp()
        r = prep(2, work, '--agent', 'codex')
        self.assertEqual(r.returncode, 0, r.stderr)
        line = next(l for l in r.stdout.splitlines() if 'codex exec ' in l and l.lstrip().startswith('cd '))
        self.assertIn('--skip-git-repo-check', line)
        self.assertIn('--sandbox workspace-write', line)
        self.assertNotIn('danger-full-access', line)
        self.assertNotIn('dangerously-bypass', line)

    def test_codex_defaults_precede_extra(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location('rp', os.path.join(ROOT, 'tests', 'run_persona.py'))
        rp = importlib.util.module_from_spec(spec); spec.loader.exec_module(rp)
        self.assertEqual(rp.CODEX_DEFAULT, ['--skip-git-repo-check', '--sandbox', 'workspace-write'])
        with open(os.path.join(ROOT, 'tests', 'run_persona.py'), encoding='utf-8') as fh: src = fh.read()
        self.assertIn("['codex', 'exec', *CODEX_DEFAULT, *net_args, *a.extra, prompt]", src)

    def test_overwrite_removes_old_sandbox_on_request(self):
        work = tempfile.mkdtemp()
        self.assertEqual(prep(1, work).returncode, 0)
        self.assertEqual(prep(1, work).returncode, 0)
        self.assertEqual(len(sandboxes(work, 1)), 2)
        r = prep(1, work, '--overwrite')
        self.assertEqual(r.returncode, 0, r.stderr)
        fixed = os.path.join(work, 'dvm-run-1')
        self.assertTrue(os.path.isdir(fixed), 'нет фиксированной песочницы после --overwrite')
        marker = os.path.join(fixed, 'marker.txt')
        with open(marker, 'w', encoding='utf-8') as fh: fh.write('old\n')
        self.assertEqual(prep(1, work, '--overwrite').returncode, 0)
        self.assertFalse(os.path.exists(marker), 'по --overwrite старая песочница должна быть удалена')
        self.assertEqual(len(sandboxes(work, 1)), 2, 'без --overwrite прежние песочницы не трогаются')

    def test_missing_agent_is_reported(self):
        r = subprocess.run([PY, os.path.join(ROOT, 'tests', 'run_persona.py'), '--persona', '1', '--agent', 'custom', '--cmd', 'dvm-no-such-agent-xyz {prompt_file}',
                            '--workdir', tempfile.mkdtemp()], capture_output=True, text=True)
        self.assertNotEqual(r.returncode, 0)

    def test_owner_scripts_are_up_to_date(self):
        r = subprocess.run([PY, os.path.join(ROOT, 'tests', 'personas', 'build_owner_scripts.py'), '--check'], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout)

    def run_custom(self, cmd, timeout=None):
        work = tempfile.mkdtemp()
        args = [PY, os.path.join(ROOT, 'tests', 'run_persona.py'), '--persona', '1', '--agent', 'custom', '--cmd', cmd, '--workdir', work]
        if timeout is not None: args += ['--timeout', str(timeout)]
        return subprocess.run(args, capture_output=True, text=True)

    def test_agent_nonzero_exit_gives_code_3(self):
        """V-03: падение агента не должно выглядеть как успешная или обычная проверка."""
        r = self.run_custom('exit 5')
        self.assertEqual(r.returncode, 3, r.stdout + r.stderr)
        self.assertIn('агент завершился с ошибкой (код 5)', r.stdout)
        self.assertIn('проверка неполная', r.stdout)

    def test_agent_timeout_gives_code_3(self):
        r = self.run_custom('sleep 5', timeout=1)
        self.assertEqual(r.returncode, 3, r.stdout + r.stderr)
        self.assertIn('проверка неполная', r.stdout)


    def e2e(self, agent_file, persona):
        work = tempfile.mkdtemp()
        cmd = f'{PY} {os.path.join(ROOT, "tests", "fixtures", "fake_agents", agent_file)}'
        return subprocess.run([PY, os.path.join(ROOT, 'tests', 'run_persona.py'), '--persona', str(persona), '--agent', 'custom', '--cmd', cmd, '--workdir', work],
                              capture_output=True, text=True)

    def test_end_to_end_good_fake_agent_passes(self):
        """Харнес от начала до конца: хороший агент проходит проверку без FAIL."""
        r = self.e2e('good_agent.py', 1)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn('FAIL нет', r.stdout)

    def test_end_to_end_bad_fake_agent_is_caught(self):
        """Плохой агент (правит набор, пишет секрет, pie, цвета вне токенов) должен быть пойман."""
        r = self.e2e('bad_agent.py', 3)
        self.assertEqual(r.returncode, 1, r.stdout)
        for expected in ('FAIL  scope', 'FAIL  secrets', 'FAIL  forms', 'FAIL  tokens', 'FAIL  honesty'):
            self.assertIn(expected, r.stdout, expected)


if __name__ == '__main__':
    unittest.main()
