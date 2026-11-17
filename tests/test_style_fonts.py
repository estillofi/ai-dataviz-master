"""Скелеты пяти стилей используют рекомендованные открытые шрифты из 02-references/fonts/README.md, без фирменных шрифтов изданий и ложного курсива."""
import pathlib
import re
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
STYLES = ROOT / '02-references' / 'styles'
FONTS = ROOT / '02-references' / 'fonts'

EXPECTED = {   # стиль -> {css-переменная: первое семейство}
    'yau': {'--font': 'Source Sans 3'},
    'nyt': {'--font-head': 'Source Serif 4', '--font-ui': 'Source Sans 3'},
    'fragapane': {'--font-display': 'Literata', '--font-ui': 'Manrope'},
    'bremer': {'--font': 'Manrope'},
    'lupi': {'--font-display': 'Literata', '--font-ui': 'Manrope'},
}
FORBIDDEN = ('Cheltenham', 'Libre Franklin', 'Franklin Gothic', '"Inter"', 'Space Grotesk', 'Iowan Old Style')
FILES = {'Source Sans 3': 'SourceSans3.ttf', 'Source Serif 4': 'SourceSerif4.ttf', 'Literata': 'Literata.ttf', 'Manrope': 'Manrope.ttf'}


class StyleFontsTest(unittest.TestCase):
    def test_skeleton_and_tokens_use_recommended_families(self):
        for style, want in EXPECTED.items():
            text = (STYLES / f'{style}.md').read_text(encoding='utf-8')
            for var, family in want.items():
                decls = re.findall(re.escape(var) + r'\s*:\s*([^;]+);', text)
                self.assertTrue(decls, f'{style}: нет {var}')
                for d in decls:
                    first = d.split(',')[0].strip().strip('"\'')
                    self.assertEqual(first, family, f'{style}: {var} начинается с {first!r}, ожидалось {family!r}')
                self.assertTrue((FONTS / FILES[family]).is_file(), FILES[family])

    def test_no_publication_or_unavailable_fonts(self):
        for style in EXPECTED:
            text = (STYLES / f'{style}.md').read_text(encoding='utf-8')
            code = '\n'.join(re.findall(r'```(?:css|html)\n(.*?)```', text, re.S))   # упоминание в обосновании допустимо, в коде нет
            for name in FORBIDDEN:
                self.assertNotIn(name, code, f'{style}: {name}')

    def test_no_synthetic_italic_in_skeletons(self):
        """У файлов шрифтов только прямое начертание: italic в скелете даёт ложный курсив."""
        for style in EXPECTED:
            text = (STYLES / f'{style}.md').read_text(encoding='utf-8')
            for block in re.findall(r'<style>(.*?)</style>', text, re.S):
                self.assertNotRegex(block, r'font\s*:\s*italic|font-style\s*:\s*italic', style)


if __name__ == '__main__':
    unittest.main()
