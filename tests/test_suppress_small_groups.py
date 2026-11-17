import importlib.util, os, subprocess, sys, unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
spec = importlib.util.spec_from_file_location('ssg', os.path.join(ROOT, 'tools', 'suppress_small_groups.py'))
ssg = importlib.util.module_from_spec(spec); spec.loader.exec_module(ssg)


class SuppressionTests(unittest.TestCase):
    """Находка внешнего тестирования F01: одной метки «мало данных» недостаточно."""

    def test_two_groups_n2_and_n10_publish_no_breakdown(self):
        # воспроизведение из отчёта: группы n=2 и n=10 при пороге 5
        r = ssg.suppress({'A': 2, 'B': 10}, 5)
        self.assertFalse(r['publishable_breakdown'])
        self.assertEqual(r['shown'], {})
        self.assertEqual(sorted(r['hidden']), ['A', 'B'])

    def test_single_small_group_is_not_recoverable_by_subtraction(self):
        # три группы: 2 мало, 14 и 12 нормально. Если скрыть только «2» и показать итог 28, значение восстановимо
        r = ssg.suppress({'7А': 14, '7Б': 12, '8Б': 2}, 5)
        self.assertGreaterEqual(len(r['hidden']), 2, 'должна быть скрыта ещё одна группа')
        shown_sum = sum(r['shown'].values())
        self.assertTrue(r['other'] is None or r['other'] >= 5)
        # итог минус показанное = «Другое», которое объединяет ≥ 2 групп и не меньше порога
        if r['other'] is not None:
            self.assertEqual(r['total'] - shown_sum, r['other'])

    def test_complementary_group_is_the_smallest_remaining(self):
        r = ssg.suppress({'a': 1, 'b': 8, 'c': 9, 'd': 30}, 5)
        self.assertIn('a', r['hidden']); self.assertIn('b', r['hidden'])
        self.assertEqual(r['other'], 9)

    def test_nothing_to_hide(self):
        r = ssg.suppress({'a': 10, 'b': 12, 'c': 7}, 5)
        self.assertEqual(r['hidden'], [])
        self.assertTrue(r['publishable_breakdown'])

    def test_two_small_groups_with_sum_over_threshold(self):
        r = ssg.suppress({'a': 3, 'b': 3, 'c': 20}, 5)
        self.assertEqual(sorted(r['hidden']), ['a', 'b'])
        self.assertEqual(r['other'], 6)

    def test_two_small_groups_with_sum_under_threshold_hide_next(self):
        r = ssg.suppress({'a': 1, 'b': 2, 'c': 9, 'd': 20}, 5)
        self.assertIn('c', r['hidden'])
        self.assertGreaterEqual(r['other'], 5)

    def test_total_below_k_not_published(self):
        r = ssg.suppress({'a': 1, 'b': 2}, 5)
        self.assertIsNone(r['total'])

    def test_invalid_input(self):
        with self.assertRaises(ValueError): ssg.suppress({'a': -1}, 5)
        with self.assertRaises(ValueError): ssg.suppress({'a': 1.5}, 5)
        with self.assertRaises(ValueError): ssg.suppress({'a': 3}, 1)

    def test_cli_pairs(self):
        r = subprocess.run([sys.executable, os.path.join(ROOT, 'tools', 'suppress_small_groups.py'), '--pairs', '7А=14', '7Б=12', '8Б=2'],
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn('Скрыто', r.stdout)

    def test_cli_csv_on_school_fixture(self):
        import csv, tempfile, collections
        src = os.path.join(ROOT, 'tests', 'fixtures', 'school', 'school_scores.csv')
        # число уникальных учеников по классам
        seen = collections.defaultdict(set)
        with open(src, encoding='utf-8', newline='') as fh:
            for row in csv.DictReader(fh): seen[row['class']].add(row['student'])
        d = tempfile.mkdtemp(); p = os.path.join(d, 'c.csv')
        with open(p, 'w', encoding='utf-8', newline='') as fh:
            w = csv.writer(fh); w.writerow(['class', 'n']); [w.writerow([c, len(s)]) for c, s in seen.items()]
        r = subprocess.run([sys.executable, os.path.join(ROOT, 'tools', 'suppress_small_groups.py'), '--csv', p, '--group-col', 'class', '--count-col', 'n', '--json'],
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn('8Б', r.stdout)

    def test_cli_bad_pair(self):
        r = subprocess.run([sys.executable, os.path.join(ROOT, 'tools', 'suppress_small_groups.py'), '--pairs', 'нет_знака'], capture_output=True, text=True)
        self.assertNotEqual(r.returncode, 0)


if __name__ == '__main__':
    unittest.main()
