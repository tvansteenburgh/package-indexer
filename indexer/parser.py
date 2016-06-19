import logging

log = logging.getLogger(__name__)

COMMANDS = ('INDEX', 'REMOVE', 'QUERY')


def parse_line(line):
    """Parse a line and return a `:class:Message` object.

    :param str line: A line received from a network client
    :return: A `:class:Message` object, or None if the line can't be parsed


    A well-formed line will follow this pattern:

        <command>|<package>|<dependencies>\n

    Where:
    * `<command>` is mandatory, and is either `INDEX`, `REMOVE`, or `QUERY`
    * `<package>` is mandatory, the name of the package referred to by the
      command, e.g. `mysql`, `openssl`, `pkg-config`, `postgresql`, etc.
    * `<dependencies>` is optional, and if present it will be a comma-
      delimited list of packages that need to be present before `<package>`
      is installed. e.g. `cmake,sphinx-doc,xz`
    * The line always ends with the character `\n`

    Here are some sample lines:

        INDEX|cloog|gmp,isl,pkg-config\n
        INDEX|ceylon|\n
        REMOVE|cloog|\n
        QUERY|cloog|\n

    """
    try:
        cmd, pkg, deps = line.rstrip().split('|')
    except ValueError:
        return None

    if cmd not in COMMANDS:
        return None

    if deps:
        deps = deps.split(',')
    else:
        deps = []

    return Message(cmd, pkg, deps)


class Message:
    """A message received from a client.

    """
    def __init__(self, cmd, pkg, deps):
        self.command = cmd
        self.package = pkg
        self.dependencies = deps
