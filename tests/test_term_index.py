import re
import unittest

from term_index import TermIndex


class TermIndexTests(unittest.TestCase):
    def test_exact_matches_include_overlapping_different_terms(self):
        terms = ["示例银行", "示例银行北京分行", "北京分行"]
        text = "示例银行北京分行。示例银行"
        found = list(TermIndex(terms).find(text))
        for term in terms:
            self.assertEqual(
                [(match.start(), match.end()) for match in re.finditer(re.escape(term), text)],
                [(start, end) for value, start, end in found if value == term],
            )


if __name__ == "__main__":
    unittest.main()
