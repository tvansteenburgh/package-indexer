import unittest

from indexer import parser


class ParserTest(unittest.TestCase):
    def test_malformed_line(self):
        line = 'foo'
        result = parser.parse_line(line)
        self.assertIsNone(result)

    def test_invalid_command(self):
        line = 'UPDATE|mypkg|dep1,dep2\n'
        result = parser.parse_line(line)
        self.assertIsNone(result)

    def test_no_deps(self):
        line = 'INDEX|mypkg|\n'
        result = parser.parse_line(line)
        self.assertIsInstance(result, parser.Message)
        self.assertEqual(result.command, 'INDEX')
        self.assertEqual(result.package, 'mypkg')
        self.assertEqual(result.dependencies, [])

    def test_one_dep(self):
        line = 'INDEX|mypkg|mydep\n'
        result = parser.parse_line(line)
        self.assertIsInstance(result, parser.Message)
        self.assertEqual(result.command, 'INDEX')
        self.assertEqual(result.package, 'mypkg')
        self.assertEqual(result.dependencies, ['mydep'])

    def test_multi_deps(self):
        line = 'INDEX|mypkg|dep1,dep2\n'
        result = parser.parse_line(line)
        self.assertIsInstance(result, parser.Message)
        self.assertEqual(result.command, 'INDEX')
        self.assertEqual(result.package, 'mypkg')
        self.assertEqual(result.dependencies, ['dep1', 'dep2'])
