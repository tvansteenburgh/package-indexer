import asyncio
import shutil
import tempfile
import unittest

from indexer import index
from indexer import server

OK = 'OK\n'
FAIL = 'FAIL\n'
ERROR = 'ERROR\n'


class IndexServerTest(unittest.TestCase):
    def setUp(self):
        self.loop = asyncio.get_event_loop()
        self.coro = self.loop.run_until_complete

        host, port = '0.0.0.0', 8080
        fsi = self._make_index()
        self.server = server.IndexServer(fsi, host, port, self.loop)
        self.server.start()

        self.client = Client(host, port, self.loop)
        self.client.connect()

    def tearDown(self):
        '''
        self.loop.run_until_complete(
            asyncio.gather(*asyncio.Task.all_tasks()))
        '''
        self.client.close()
        self.server.stop()

    def _make_index(self):
        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp)

        return index.FilesystemIndex(tmp, self.loop)

    def test_malformed_request(self):
        self.assertEqual(self.client.send('foo'), ERROR)

    def test_index(self):
        msg = 'INDEX|mypackage|'
        self.assertEqual(self.client.send(msg), OK)

    def test_index_duplicate(self):
        msg = 'INDEX|mypackage|'
        self.assertEqual(self.client.send(msg), OK)
        self.assertEqual(self.client.send(msg), OK)

    def test_index_fails_on_missing_deps(self):
        msg = 'INDEX|mypackage|mydep1'
        self.assertEqual(self.client.send(msg), FAIL)

    def test_remove_unindexed_package(self):
        msg = 'REMOVE|mypackage|'
        self.assertEqual(self.client.send(msg), OK)

    def test_remove_fails_due_to_dependents(self):
        self.client.send('INDEX|mydep1|')
        self.client.send('INDEX|mypackage|mydep1')

        msg = 'REMOVE|mydep1|'
        self.assertEqual(self.client.send(msg), FAIL)

    def test_remove_package_and_dependencies(self):
        self.client.send('INDEX|mydep1|')
        self.client.send('INDEX|mypackage|mydep1')

        msg = 'REMOVE|mypackage|'
        self.assertEqual(self.client.send(msg), OK)

        msg = 'REMOVE|mydep1|'
        self.assertEqual(self.client.send(msg), OK)

    def test_query_unindexed(self):
        msg = 'QUERY|mypackage|'
        self.assertEqual(self.client.send(msg), FAIL)

    def test_query_indexed(self):
        self.client.send('INDEX|mypackage|')

        msg = 'QUERY|mypackage|'
        self.assertEqual(self.client.send(msg), OK)


class Client:
    """A simple client for testing our server

    """
    def __init__(self, host, port, loop):
        self.host = host
        self.port = port
        self.loop = loop
        self.reader = None
        self.writer = None

    def connect(self):
        self.reader, self.writer = self.loop.run_until_complete(
            asyncio.open_connection(
                self.host, self.port, loop=self.loop))

    def send(self, text):
        self.writer.write((text + '\n').encode())
        return self.loop.run_until_complete(self.recv())

    async def recv(self):
        return (await self.reader.readline()).decode()

    def close(self):
        if self.writer:
            self.writer.close()
