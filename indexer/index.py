import abc
import asyncio
import io
import os
import string

from pathlib import Path


class Index:
    """Base class for package index implementations"""

    __metaclass__ = abc.ABCMeta

    @abc.abstractmethod
    def index(self, package, dependencies):
        """Add a new package to the index

        Implementations should:

        Return True if the package could be indexed or it was already present.

        Return False if the package cannot be indexed because some of its
        dependencies aren't indexed yet.

        """
        pass

    @abc.abstractmethod
    def remove(self, package):
        """Remove a package from the index

        Implementations should:

        Return True if the package could be removed from the index, or if the
        package wasn't indexed to begin with.

        Return False if the package could not be removed because some other
        indexed package depends on it.

        """
        pass

    @abc.abstractmethod
    def query(self, package):
        """Query the index for the existence of a package

        Implementations should:

        Return True if the package is indexed.

        Return False if the package is not indexed.

        """
        pass


class FilesystemIndex(Index):
    """A package index that uses a filesystem for storage.

    The filesystem is not necessarily local, and other indexing servers may be
    sharing the index location.

    """
    def __init__(self, root_path, loop):
        """Initialize an index

        This is called before the event loop starts, so we don't have to
        worry about blocking here.

        :param root_path: A string or Path object pointing to the root
            directory of the index on disk. This may be an empty dir or an
            already-existing index (full of dirs and files).
        :param loop: The asyncio event loop in which we are running. File io
            operations should take care not to block the event loop.

        """
        self.root_path = Path(str(root_path))
        self.loop = loop
        self.executor = None
        self.lock = asyncio.Lock()
        self._bootstrap()

    def _bootstrap(self):
        """Set up the index directory structure

        """
        for dir_ in ('forward', 'reverse'):
            dir_path = self.root_path / dir_
            dir_path.mkdir(exist_ok=True)
            for leaf in string.ascii_lowercase:
                leaf_path = dir_path / leaf
                leaf_path.mkdir(exist_ok=True)

    async def index(self, package, dependencies):
        """Add a new package to the index

        :param str package: The package name
        :param list dependencies: List of package dependencies (package names)
        :return: True if the package could be indexed, or already exists in
            the index. False if indexing failed because not all dependencies
            are indexed.

        """
        if await self.query(package):
            # Package is already in the index
            return True

        for dep in dependencies:
            if not await self.query(dep):
                # One of our deps isn't indexed, can't continue
                return False

        with (await self.lock):
            forward = await self._forward_index(package, dependencies)
            reverse = await self._reverse_index(package, dependencies)
        return forward and reverse

    async def remove(self, package):
        """Remove a package from the index

        :param str package: The package name to remove
        :return: True if the package could be removed from the index, or if the
            package wasn't indexed to begin with. False if the package could
            not be removed because some other indexed package depends on it.

        """
        if not await self.query(package):
            # Package isn't indexed
            return True

        if await self._is_depended_on(package):
            return False

        with (await self.lock):
            result = await self._remove_package(package)
        return result

    async def query(self, package):
        """Query the index for existence of ``package``

        :param str package: The package name
        :return: True if package is indexed, else False.

        """
        index_path = self._index_path(package)
        return await self._exists(index_path)

    async def _is_depended_on(self, package):
        """Return True if ``package`` is depended on by other packages

        """
        file_path = self._reverse_index_path(package)
        return await self._exists(file_path)

    def _index_path(self, package):
        """Return path to forward index file for ``package``

        The forward index file maps a package (the file name) to the
        packages it depends on (the file contents, a comma-delimited list
        of package names).

        """
        return self.root_path / 'forward' / package[0] / package

    def _reverse_index_path(self, package):
        """Return path to reverse index file for ``package``

        The reverse index file maps a package (the file name) to the
        packages that depend on it (the file contents, a comma-delimited
        list of package names).

        """
        return self.root_path / 'reverse' / package[0] / package

    async def _forward_index(self, package, dependencies):
        """Write the forward index file for ``package``

        """
        index_path = self._index_path(package)

        def create_index_entry(index_path, content):
            with io.open(index_path, 'w') as f:
                f.write(content)
            return True

        return await self.loop.run_in_executor(
            self.executor,
            create_index_entry, str(index_path), ','.join(dependencies))

    async def _reverse_index(self, package, dependencies):
        """Add ``package`` to the reverse index file for each dependency

        """
        def add_dependent(path, package):
            with io.open(path, 'a+') as f:
                f.seek(0)
                content = f.read()
                f.seek(0)
                f.truncate()
                if not content:
                    f.write(package)
                    return
                else:
                    deps = set(content.split(','))
                    deps.add(package)
                    f.write(','.join(deps))

        for dep in dependencies:
            file_path = self._reverse_index_path(dep)
            await self.loop.run_in_executor(
                self.executor, add_dependent, str(file_path), package)

        return True

    def _remove_dependent(self, package, dependent):
        """Remove ``dependent`` from the reverse index file for ``package``

        If dependent was the last entry in the file, delete the file.

        """
        file_path = str(self._reverse_index_path(package))
        should_delete = False

        with io.open(file_path, 'a+') as f:
            f.seek(0)
            content = f.read()
            f.seek(0)
            f.truncate()

            deps = set(content.split(','))
            deps.remove(dependent)
            if not deps:
                should_delete = True
            else:
                f.write(','.join(deps))

        if should_delete:
            os.remove(file_path)

    async def _remove_package(self, package):
        """Remove a package from the index

        This involves two steps:

            - For each dependency, remove package from its reverse index file,
              possibly deleting the file if package was the only entry
            - Delete the forward index file for package

        """
        index_path = self._index_path(package)

        def remove_package(path):
            with io.open(path, 'r') as f:
                content = f.read()
                if content:
                    deps = set(content.split(','))
                    for dep in deps:
                        self._remove_dependent(dep, package)
            os.remove(path)
            return True

        return await self.loop.run_in_executor(
            self.executor, remove_package, str(index_path))

    async def _exists(self, path):
        """Return True if ``path`` exists

        :param path: A :class:`pathlib.Path` instance

        """
        return await self.loop.run_in_executor(self.executor, path.exists)
