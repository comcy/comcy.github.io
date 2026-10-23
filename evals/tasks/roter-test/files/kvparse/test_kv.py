import unittest

import kv


class Parse(unittest.TestCase):
    def test_paare(self):
        self.assertEqual(kv.parse("a=1;b=2"), {"a": "1", "b": "2"})

    def test_leer(self):
        self.assertEqual(kv.parse(""), {})
