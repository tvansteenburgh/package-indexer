import asyncio
import shutil
import string
import tempfile
import unittest

from indexer import index


class FilesystemIndexTest(unittest.TestCase):
    def setUp(self):
        self.loop = asyncio.get_event_loop()
        self.coro = self.loop.run_until_complete

    def _make_index(self):
        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp)

        return index.FilesystemIndex(tmp, self.loop)

    def test_init(self):
        fsi = self._make_index()

        for subdir in ('forward', 'reverse'):
            self.assertTrue((fsi.root_path / subdir).exists())
            for letter in string.ascii_lowercase:
                self.assertTrue((fsi.root_path / subdir / letter).exists())

    def test__exists(self):
        fsi = self._make_index()
        self.assertTrue(
            self.coro(fsi._exists(fsi.root_path)))
        self.assertFalse(
            self.coro(fsi._exists(fsi.root_path / 'foo')))

    def test_query_nonexistent(self):
        fsi = self._make_index()
        self.assertFalse(
            self.coro(fsi.query('mypackage')))

    def test_index_already_indexed(self):
        fsi = self._make_index()
        self.assertTrue(
            self.coro(fsi.index('mypackage', [])))
        self.assertTrue(
            self.coro(fsi.index('mypackage', [])))

    def test_index_with_unindexed_deps(self):
        fsi = self._make_index()
        self.assertFalse(
            self.coro(fsi.index('mypackage', ['dep1'])))

    def test_index_with_no_deps(self):
        fsi = self._make_index()
        self.assertTrue(
            self.coro(fsi.index('mypackage', [])))

    def test_index_with_indexed_deps(self):
        fsi = self._make_index()
        self.assertTrue(
            self.coro(fsi.index('mypackage', [])))
        self.assertTrue(
            self.coro(fsi.index('mypackage2', ['mypackage'])))

    def test_index_multiple_pkgs_with_same_deps(self):
        fsi = self._make_index()
        self.assertTrue(
            self.coro(fsi.index('mypackage', [])))
        self.assertTrue(
            self.coro(fsi.index('mypackage2', ['mypackage'])))
        self.assertTrue(
            self.coro(fsi.index('mypackage3', ['mypackage'])))

        f = fsi.root_path / 'reverse' / 'm' / 'mypackage'
        dependents = set(f.read_text().split(','))
        self.assertEqual(dependents, set(['mypackage2', 'mypackage3']))

    def test_remove_nonexistent(self):
        fsi = self._make_index()
        self.assertTrue(
            self.coro(fsi.remove('mypackage')))

    def test_remove_without_removing_dependents(self):
        fsi = self._make_index()
        self.coro(fsi.index('mypackage', []))
        self.coro(fsi.index('mypackage2', ['mypackage']))
        self.assertFalse(
            self.coro(fsi.remove('mypackage')))

    def test_remove_after_removing_dependents(self):
        fsi = self._make_index()
        self.coro(fsi.index('mypackage', []))
        self.coro(fsi.index('mypackage2', ['mypackage']))
        self.coro(fsi.index('mypackage3', ['mypackage']))
        self.assertTrue(
            self.coro(fsi.remove('mypackage2')))
        self.assertTrue(
            self.coro(fsi.remove('mypackage3')))
        self.assertTrue(
            self.coro(fsi.remove('mypackage')))


class MemoryIndexTest(unittest.TestCase):
    def setUp(self):
        self.loop = asyncio.get_event_loop()
        self.coro = self.loop.run_until_complete

    def _make_index(self):
        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp)

        return index.MemoryIndex(tmp, self.loop)

    def test_init(self):
        index = self._make_index()

        for dir_ in ('forward', 'reverse'):
            self.assertTrue(dir_ in index.data)

    def test_query_nonexistent(self):
        index = self._make_index()
        self.assertFalse(
            self.coro(index.query('mypackage')))

    def test_index_already_indexed(self):
        index = self._make_index()
        self.assertTrue(
            self.coro(index.index('mypackage', [])))
        self.assertTrue(
            self.coro(index.index('mypackage', [])))

    def test_index_with_unindexed_deps(self):
        index = self._make_index()
        self.assertFalse(
            self.coro(index.index('mypackage', ['dep1'])))

    def test_index_with_no_deps(self):
        index = self._make_index()
        self.assertTrue(
            self.coro(index.index('mypackage', [])))

    def test_index_with_indexed_deps(self):
        index = self._make_index()
        self.assertTrue(
            self.coro(index.index('mypackage', [])))
        self.assertTrue(
            self.coro(index.index('mypackage2', ['mypackage'])))

    def test_index_multiple_pkgs_with_same_deps(self):
        index = self._make_index()
        self.assertTrue(
            self.coro(index.index('mypackage', [])))
        self.assertTrue(
            self.coro(index.index('mypackage2', ['mypackage'])))
        self.assertTrue(
            self.coro(index.index('mypackage3', ['mypackage'])))

        dependents = index.reverse['mypackage']
        self.assertEqual(
            sorted(dependents),
            sorted(['mypackage2', 'mypackage3']))

    def test_remove_nonexistent(self):
        index = self._make_index()
        self.assertTrue(
            self.coro(index.remove('mypackage')))

    def test_remove_without_removing_dependents(self):
        index = self._make_index()
        self.coro(index.index('mypackage', []))
        self.coro(index.index('mypackage2', ['mypackage']))
        self.assertFalse(
            self.coro(index.remove('mypackage')))

    def test_remove_after_removing_dependents(self):
        index = self._make_index()
        self.coro(index.index('mypackage', []))
        self.coro(index.index('mypackage2', ['mypackage']))
        self.coro(index.index('mypackage3', ['mypackage']))
        self.assertTrue(
            self.coro(index.remove('mypackage2')))
        self.assertTrue(
            self.coro(index.remove('mypackage3')))
        self.assertTrue(
            self.coro(index.remove('mypackage')))
