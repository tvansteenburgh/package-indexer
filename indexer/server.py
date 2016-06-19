import asyncio
import logging

from . import parser

log = logging.getLogger(__name__)


class Server:
    """Basic TCP server for a line-based protocol

    """
    def __init__(self, host, port, loop=None):
        """Initialize the server

        :param str host: Host name or ip address
        :param int port: Port on which to listen
        :param loop: An asyncio-compatible event loop, or None to use default

        """
        self.host = host
        self.port = port
        self.loop = loop or asyncio.get_event_loop()
        self.server = None

    def _handle_connection(self, reader, writer):
        """Handle each incoming client connection

        :param reader: A :class:`asyncio.StreamReader` instance
        :param writer: A :class:`asyncio.StreamWriter` instance

        """
        self.loop.create_task(self._handle_request(reader, writer))

    async def _handle_request(self, reader, writer):
        """Handle each request from a connected client

        :param reader: A :class:`asyncio.StreamReader` instance
        :param writer: A :class:`asyncio.StreamWriter` instance

        """
        try:
            while True:
                data = (await reader.readline()).decode().rstrip()
                if not data:  # an empty string means the client disconnected
                    break

                await self.handle_line(data, reader, writer)
                await writer.drain()
        except ConnectionError:
            pass

    async def handle_line(self, line, reader, writer):
        """Handle each line from a client

        :param str line: Line of text data
        :param reader: A :class:`asyncio.StreamReader` instance
        :param writer: A :class:`asyncio.StreamWriter` instance

        Default implementation is a no-op.

        """
        return await asyncio.sleep(0)

    def start(self):
        """Start listening on our host/port

        """
        self.server = self.loop.run_until_complete(
            asyncio.start_server(
                self._handle_connection, self.host, self.port, loop=self.loop))
        log.info('Serving on {}'.format(self.server.sockets[0].getsockname()))

    def stop(self):
        """Stop listening and close the socket

        """
        if self.server is not None:
            self.server.close()
            self.loop.run_until_complete(self.server.wait_closed())
            self.server = None


class IndexServer(Server):
    """TCP server that implements our package indexing protocol

    """
    def __init__(self, index, host, port, loop=None):
        """Initialize the server

        :param index: A :class:`index.Index` instance
        :param str host: Host name or ip address
        :param int port: Port on which to listen
        :param loop: An asyncio-compatible event loop, or None to use default

        """
        super(IndexServer, self).__init__(host, port, loop)
        self.index = index
        self.message_count = 0

    def _get_message_id(self):
        """Return a unique integer message id

        The id is unique to the server process. Useful for correlating
        requests/responses in log messages.

        """
        self.message_count += 1
        return self.message_count

    async def handle_line(self, line, reader, writer):
        """Handle each incoming line from a connected client

        :param str line: A line of text data
        :param reader: A :class:`asyncio.StreamReader` instance
        :param writer: A :class:`asyncio.StreamWriter` instance

        """
        msg_id = self._get_message_id()
        log.debug('%s:%s Received line: %s', id(writer), msg_id, line)

        msg = parser.parse_line(line)

        if not msg:
            self._write_line(writer, msg_id, 'ERROR')
            return

        command_method = getattr(self, 'cmd_' + msg.command.lower())
        if await command_method(msg):
            self._write_line(writer, msg_id, 'OK')
        else:
            self._write_line(writer, msg_id, 'FAIL')

    async def cmd_index(self, msg):
        """Index a package

        :param msg: A :class:`indexer.parser.Message` instance

        """
        return await self.index.index(msg.package, msg.dependencies)

    async def cmd_remove(self, msg):
        """Remove a package from the index

        :param msg: A :class:`indexer.parser.Message` instance

        """
        return await self.index.remove(msg.package)

    async def cmd_query(self, msg):
        """Query the index for a package

        :param msg: A :class:`indexer.parser.Message` instance

        """
        return await self.index.query(msg.package)

    def _write_line(self, writer, message_id, text):
        """Write ``text`` as \\n-terminated bytes on ``writer``

        :param writer: A :class:`asyncio.StreamWriter` instance
        :param int message_id: Message id
        :param str text: Text data to write

        """
        line = (text + '\n').encode()
        writer.write(line)

        log.debug('%s:%s Sent line: %s', id(writer), message_id, line)
        return
