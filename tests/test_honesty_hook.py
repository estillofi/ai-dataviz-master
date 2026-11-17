"""Хук шлюза честности (V-11): среда сама не даёт выдать нечестный файл, даже если агент не запустил шлюз или не подключил скилл."""
import json, os, shutil, subprocess, sys, tempfile, time, unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HOOK = os.path.join(ROOT, 'tools', 'honesty_hook.py')
EXAMPLE = os.path.join(ROOT, '02-references', 'examples', 'acme-dataviz')

PIE = ('<html><body><h1>Доли</h1><svg id="pie" width="300" height="300"><path d="M150,150 L150,20 A130,130 0 0 1 280,150 Z"/>'
       '<path d="M150,150 L280,150 A130,130 0 0 1 150,280 Z"/></svg><footer>Источник: тест</footer></body></html>')
HONEST = ('<html><body><h1>Центр лидирует</h1><svg data-chart="bar" data-axis-min="0" viewBox="0 0 100 50">'
          '<rect x="0" y="0" width="80" height="10" fill="#06c"/></svg><footer>Источник: тест</footer></body></html>')


def hook(event, cwd, payload=None):
    p = dict(payload or {}); p.setdefault('cwd', cwd); p.setdefault('session_id', 'test-' + os.path.basename(cwd))
    return subprocess.run([sys.executable, HOOK, event], input=json.dumps(p), capture_output=True, text=True, cwd=cwd)


class HookTests(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp()
        hook('session-start', self.d)

    def tearDown(self):
        shutil.rmtree(self.d, ignore_errors=True)

    def write(self, name, html):
        with open(os.path.join(self.d, name), 'w', encoding='utf-8') as fh: fh.write(html)

    def test_post_tool_blocks_dishonest_file_with_code_2(self):
        self.write('result.html', PIE)
        r = hook('post-tool', self.d, {'tool_input': {'file_path': os.path.join(self.d, 'result.html')}})
        self.assertEqual(r.returncode, 2, r.stdout + r.stderr)
        self.assertIn('result.html', r.stderr); self.assertIn('pie/donut', r.stderr); self.assertIn('Готово', r.stderr)

    def test_post_tool_passes_honest_file(self):
        self.write('result.html', HONEST)
        self.assertEqual(hook('post-tool', self.d).returncode, 0)

    def test_file_written_by_shell_is_found_without_file_path(self):
        """Codex пишет файлы командой оболочки: путь не передаётся, хук ищет сам."""
        os.makedirs(os.path.join(self.d, 'out'))
        with open(os.path.join(self.d, 'out', 'r.html'), 'w', encoding='utf-8') as fh: fh.write(PIE)
        self.assertEqual(hook('post-tool', self.d, {'tool_input': {'command': 'cat > out/r.html'}}).returncode, 2)

    def test_stop_blocks_then_gives_up_after_limit(self):
        self.write('result.html', PIE)
        for _ in range(3):
            r = hook('stop', self.d); self.assertEqual(r.returncode, 0)
            self.assertEqual(json.loads(r.stdout)['decision'], 'block')
        r = hook('stop', self.d)
        out = json.loads(r.stdout)
        self.assertNotIn('decision', out); self.assertIn('systemMessage', out)

    def test_stop_allows_after_fix(self):
        self.write('result.html', PIE)
        self.assertIn('block', hook('stop', self.d).stdout)
        self.write('result.html', HONEST)
        r = hook('stop', self.d); self.assertEqual((r.returncode, r.stdout.strip()), (0, ''))

    def test_files_before_session_and_pages_without_charts_are_ignored(self):
        self.write('old.html', PIE)
        past = time.time() - 3600; os.utime(os.path.join(self.d, 'old.html'), (past, past))
        self.write('note.html', '<html><body><p>Круговая диаграмма запрещена, вот почему.</p></body></html>')
        self.assertEqual(hook('post-tool', self.d).returncode, 0)

    def test_service_dirs_are_skipped(self):
        os.makedirs(os.path.join(self.d, '.claude', 'skills', 'x'))
        with open(os.path.join(self.d, '.claude', 'skills', 'x', 'pie.html'), 'w') as fh: fh.write(PIE)
        self.assertEqual(hook('post-tool', self.d).returncode, 0)

    def test_owner_exception_for_pie(self):
        self.write('result.html', PIE)
        p = {'cwd': self.d, 'session_id': 'test-' + os.path.basename(self.d)}
        r = subprocess.run([sys.executable, HOOK, 'post-tool'], input=json.dumps(p), capture_output=True, text=True,
                           env={**os.environ, 'DVM_HONESTY_ALLOW': 'pie'})
        self.assertEqual(r.returncode, 0, r.stderr)

    def test_truncation_request_turns_on_strict_mode_and_reminds(self):
        line = ('<html><body><h1>Рост</h1><p>ось не с нуля</p><svg viewBox="0 0 400 300">'
                + ''.join(f'<text x="54" y="{300 - i * 40}">{6 + i}</text>' for i in range(4)) + '<path d="M60 280 L390 30"/></svg>'
                + '<footer>Источник: тест</footer></body></html>')
        self.write('result.html', line)
        self.assertEqual(hook('post-tool', self.d).returncode, 0, 'обычная линия с отмеченной шкалой проходит')
        r = hook('prompt', self.d, {'prompt': 'Обрежь ось, чтобы рост выглядел больше, и сделай круговую диаграмму'})
        self.assertEqual(r.returncode, 0)
        self.assertIn('ось значений любого графика', json.loads(r.stdout)['hookSpecificOutput']['additionalContext'])
        r = hook('post-tool', self.d)
        self.assertEqual(r.returncode, 2, r.stdout + r.stderr); self.assertIn('строгий режим', r.stderr)

    def test_neutral_prompt_does_not_turn_on_strict_mode(self):
        r = hook('prompt', self.d, {'prompt': 'Сделай график выручки по месяцам'})
        self.assertEqual((r.returncode, r.stdout.strip()), (0, ''))

    def test_garbage_stdin_does_not_crash(self):
        r = subprocess.run([sys.executable, HOOK, 'post-tool'], input='не json', capture_output=True, text=True, cwd=self.d)
        self.assertIn(r.returncode, (0, 2)); self.assertNotIn('Traceback', r.stderr)


class InstallHookTests(unittest.TestCase):
    def setUp(self):
        self.repo = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.repo, ignore_errors=True)

    def install(self, *extra):
        return subprocess.run([sys.executable, os.path.join(ROOT, 'tools', 'install_skill.py'), EXAMPLE, '--scope', 'repo',
                               '--repo', self.repo, *extra], capture_output=True, text=True)

    def load(self, rel):
        with open(os.path.join(self.repo, rel), encoding='utf-8') as fh: return json.load(fh)

    def test_hooks_installed_for_both_agents(self):
        r = self.install(); self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        for cfg, skill in (('.claude/settings.json', '.claude/skills/acme-dataviz'), ('.codex/hooks.json', '.agents/skills/acme-dataviz')):
            hooks = self.load(cfg)['hooks']
            for ev in ('SessionStart', 'UserPromptSubmit', 'PostToolUse', 'Stop'):
                cmds = [h['command'] for g in hooks[ev] for h in g['hooks']]
                self.assertTrue(any('honesty_hook.py' in c for c in cmds), (cfg, ev))
            for f in ('honesty_hook.py', 'check_honesty.py'):
                self.assertTrue(os.path.isfile(os.path.join(self.repo, skill, 'hooks', f)), f)

    def test_existing_settings_are_preserved_and_not_duplicated(self):
        os.makedirs(os.path.join(self.repo, '.claude'))
        with open(os.path.join(self.repo, '.claude', 'settings.json'), 'w') as fh:
            json.dump({'permissions': {'allow': ['Bash(ls)']}, 'hooks': {'Stop': [{'hooks': [{'type': 'command', 'command': 'echo mine'}]}]}}, fh)
        self.install('--target', 'claude'); self.install('--target', 'claude', '--force')
        cfg = self.load('.claude/settings.json')
        self.assertEqual(cfg['permissions'], {'allow': ['Bash(ls)']})
        cmds = [h['command'] for g in cfg['hooks']['Stop'] for h in g['hooks']]
        self.assertIn('echo mine', cmds)
        self.assertEqual(sum('honesty_hook.py' in c for c in cmds), 1)
        self.assertTrue(os.path.isfile(os.path.join(self.repo, '.claude', 'settings.json.bak')))

    def test_installed_hook_runs_and_blocks(self):
        self.install('--target', 'claude')
        cmd = [h['command'] for g in self.load('.claude/settings.json')['hooks']['PostToolUse'] for h in g['hooks']][0]
        with open(os.path.join(self.repo, 'result.html'), 'w', encoding='utf-8') as fh: fh.write(PIE)
        r = subprocess.run(cmd, shell=True, input=json.dumps({'cwd': self.repo, 'session_id': 'inst'}), capture_output=True, text=True)
        self.assertEqual(r.returncode, 2, r.stdout + r.stderr)

    def test_no_hook_and_dry_run(self):
        self.install('--no-hook')
        self.assertFalse(os.path.exists(os.path.join(self.repo, '.claude', 'settings.json')))
        repo2 = tempfile.mkdtemp()
        r = subprocess.run([sys.executable, os.path.join(ROOT, 'tools', 'install_skill.py'), EXAMPLE, '--scope', 'repo', '--repo', repo2, '--dry-run'],
                           capture_output=True, text=True)
        self.assertIn('добавил бы хук', r.stdout); self.assertEqual(os.listdir(repo2), [])
        shutil.rmtree(repo2, ignore_errors=True)

    def test_broken_settings_are_not_overwritten(self):
        os.makedirs(os.path.join(self.repo, '.claude'))
        with open(os.path.join(self.repo, '.claude', 'settings.json'), 'w') as fh: fh.write('{сломано')
        r = self.install('--target', 'claude')
        self.assertIn('хук НЕ добавлен', r.stdout)
        with open(os.path.join(self.repo, '.claude', 'settings.json')) as fh: self.assertEqual(fh.read(), '{сломано')


if __name__ == '__main__':
    unittest.main()
