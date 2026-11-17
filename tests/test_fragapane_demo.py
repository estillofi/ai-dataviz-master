"""Check the actual Fragapane demo with zero and invalid values."""
import json
import pathlib
import re
import shutil
import subprocess
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
STYLE = ROOT / '02-references/styles/fragapane.md'

@unittest.skipUnless(shutil.which('node'), 'Node.js unavailable')
class FragapaneDemoTest(unittest.TestCase):
    def run_demo(self, values):
        text = STYLE.read_text(encoding='utf-8')
        script = re.search(r'<script>(.*?)</script>', text, re.S).group(1)
        data = [{'label': str(i), 'value': v, 'group': 'a'} for i, v in enumerate(values)]
        script = re.sub(r'const DATA = \[.*?\];', 'const DATA = ' + json.dumps(data) + ';', script, count=1, flags=re.S)
        setup = '''const nodes=[];const groups={};
        global.document={createElementNS:(_,tag)=>({tag,attrs:{},setAttribute(k,v){this.attrs[k]=v;},appendChild(n){nodes.push(n)}}),
        getElementById:id=>groups[id] ||= {appendChild(n){nodes.push(n)}}};\n'''
        return subprocess.run(['node', '-e', setup + script + '\nconsole.log(JSON.stringify(nodes));'], capture_output=True, text=True)

    def test_zero_values_have_no_petal_and_no_nan(self):
        result = self.run_demo([0, 0])
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn('NaN', result.stdout)
        self.assertFalse(any(n['tag'] == 'path' for n in json.loads(result.stdout)))

    def test_mixed_zero_and_positive_draws_one_petal(self):
        result = self.run_demo([0, 10])
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(sum(n['tag'] == 'path' for n in json.loads(result.stdout)), 1)

    def test_key_and_values_are_drawn(self):
        """Ключ «Как читать» обязателен: подпись ключа, круглые опорные значения колец и точное значение у каждого лепестка."""
        result = self.run_demo([82, 64, 47, 91])
        self.assertEqual(result.returncode, 0, result.stderr)
        texts = [n.get('textContent') for n in json.loads(result.stdout) if n['tag'] == 'text']
        self.assertIn('Как читать', texts)
        for ring in ('20', '40', '60', '80'):
            self.assertIn(ring, texts)
        for v in ('82', '64', '47', '91'):
            self.assertIn(v, texts)
        self.assertNotIn('NaN', result.stdout)

    def test_zero_only_data_has_key_but_no_rings(self):
        result = self.run_demo([0, 0])
        self.assertEqual(result.returncode, 0, result.stderr)
        nodes = json.loads(result.stdout)
        self.assertFalse(any(n['tag'] == 'circle' and n['attrs'].get('class') == 'guide' for n in nodes))
        self.assertIn('Как читать', [n.get('textContent') for n in nodes])

    def test_negative_is_rejected(self):
        result = self.run_demo([-1, 10])
        self.assertNotEqual(result.returncode, 0)

if __name__ == '__main__':
    unittest.main()
