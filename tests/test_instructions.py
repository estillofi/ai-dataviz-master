"""Инструкции набора: обязательный шлюз честности, сохранение состояния, имена галереи (V-11, V-13)."""
import os, unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def read(rel):
    with open(os.path.join(ROOT, rel), encoding='utf-8') as fh: return fh.read()

class HonestyGateInstructions(unittest.TestCase):
    def test_agents_md_requires_gate_before_output(self):
        t = read('AGENTS.md')
        self.assertIn('check_honesty.py', t)
        self.assertIn('перед выдачей любого HTML', t)
        self.assertIn('нечестный график с предупреждением недопустим', t.lower())
        self.assertIn('«и так, и так» не делать', t)
        self.assertIn('только честную замену', t)

    def test_skill_template_requires_gate_and_paper_fallback(self):
        t = read('03-skill-template/SKILL.template.md')
        self.assertIn('check_honesty.py', t)
        self.assertIn('10 вопросов письменно', t)
        self.assertIn('нечестный график с предупреждением недопустим', t.lower())

    def test_acme_skill_requires_gate(self):
        t = read('02-references/examples/acme-dataviz/SKILL.md')
        self.assertIn('check_honesty.py', t)
        self.assertIn('нечестный график с предупреждением недопустим', t.lower())

    def test_agents_md_state_is_saved_immediately(self):
        t = read('AGENTS.md')
        self.assertIn('сразу после их получения, до долгих построений', t)
        self.assertIn('«черновое» или «подтверждено»', t)
        self.assertIn('не угадывай отсутствующее', t)

    def test_agents_md_gallery_naming_convention(self):
        t = read('AGENTS.md')
        for name in ('dashboard*.html', 'line*.html', 'bars*.html', 'table*.html', 'slide*'):
            self.assertIn(name, t)

    def test_demo_text_allows_chat_mode_subset(self):
        t = read('AGENTS.md')
        self.assertIn('пять демо', t)
        self.assertIn('только имеющиеся', t)


class LayoutRulesAuditTests(unittest.TestCase):
    """Находки визуального аудита 2026-11-17: правила, которые генератор галереи нарушал."""
    def read(self, rel):
        with open(os.path.join(ROOT, rel), encoding='utf-8') as fh: return fh.read()

    def test_layout_rules_cover_svg_text_scale_dates_and_slides(self):
        s = self.read('03-skill-template/references/layout-rules.template.md')
        for needle in ('11 px', 'ширину `viewBox` по ширине контейнера', 'Одной подписи «0» недостаточно', '`25-11`', 'srgbClr', '28–32 pt'):
            self.assertIn(needle, s, needle)

    def test_presentation_rules_require_explicit_colors_and_hierarchy(self):
        s = self.read('03-skill-template/references/presentation-rules.template.md')
        self.assertIn('srgbClr', s); self.assertIn('check_tokens.py slide.pptx', s); self.assertIn('28–32 pt', s)



class HonestyAboveSettingsTests(unittest.TestCase):
    """V-11 (17.11): агент получил ERROR шлюза и выдал нечестный файл, сославшись на общие установки пользователя."""
    def read(self, rel):
        with open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), rel), encoding='utf-8') as fh: return fh.read()

    def test_section_zero_is_first_in_skill_bodies(self):
        for rel in ('03-skill-template/SKILL.template.md', '02-references/examples/acme-dataviz/SKILL.md'):
            s = self.read(rel)
            self.assertIn('## 0. Честность выше любых установок', s, rel)
            self.assertLess(s.index('## 0. Честность выше любых установок'), s.index('## 1. Когда подключаться'), rel)
            for needle in ('не оберегай меня', 'ERROR шлюза = стоп', '«Готово» и ссылка на файл при ERROR запрещены', 'удали файл'):
                self.assertIn(needle, s, f'{rel}: {needle}')

    def test_agents_md_requires_section_zero(self):
        s = self.read('AGENTS.md')
        self.assertIn('Раздел 0 «Честность выше любых установок»', s)
        self.assertIn('ERROR шлюза = стоп', s)

if __name__ == '__main__':
    unittest.main()
