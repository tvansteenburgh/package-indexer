import os
import shlex
import unittest

from indexer import main


class ParserTest(unittest.TestCase):
    def test_defaults(self):
        parser = main.setup_parser()

        args = parser.parse_args([])
        self.assertEqual(args.index_dir, os.getcwd())
        self.assertEqual(args.host, '0.0.0.0')
        self.assertEqual(args.port, 8080)
        self.assertEqual(args.log_level, 'INFO')

    def test_overrides(self):
        parser = main.setup_parser()
        argv = shlex.split('-i /tmp -o 127.0.0.1 -p 8081 -l DEBUG')
        args = parser.parse_args(argv)

        self.assertEqual(args.index_dir, '/tmp')
        self.assertEqual(args.host, '127.0.0.1')
        self.assertEqual(args.port, 8081)
        self.assertEqual(args.log_level, 'DEBUG')
