#!/usr/bin/python3.5

"""Run the DigitalOcean packaging index server

"""

import argparse
import asyncio
import logging
import os
import textwrap

from .index import FilesystemIndex
from .server import IndexServer


def setup_parser():
    parser = argparse.ArgumentParser(
        prog='do-indexer',
        description=textwrap.dedent(__doc__),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        '-i', '--index-dir',
        help='Directory location of the index',
        default=os.getcwd(),
    )
    parser.add_argument(
        '-o', '--host',
        help='Host name or ip address to bind',
        default='0.0.0.0',
    )
    parser.add_argument(
        '-p', '--port',
        help='Port to bind',
        default=8080, type=int,
    )
    parser.add_argument(
        '-l', '--log-level',
        choices=('INFO', 'DEBUG', 'WARN', 'ERROR', 'CRITICAL'),
        default='INFO',
    )

    return parser


def main():
    parser = setup_parser()
    args = parser.parse_args()

    logging.basicConfig(
        format='%(asctime)s %(levelname)s %(name)s %(message)s',
        level=getattr(logging, args.log_level),
    )

    loop = asyncio.get_event_loop()
    index = FilesystemIndex(args.index_dir, loop)
    server = IndexServer(index, args.host, args.port, loop)
    server.start()

    try:
        loop.run_forever()
    except KeyboardInterrupt:
        pass

    server.stop()
    loop.close()


if __name__ == '__main__':
    main()
