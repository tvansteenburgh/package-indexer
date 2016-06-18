# package-tree indexer: DigitalOcean Coding Challenge Solution

## Design Considerations

### Network IO

Use python3's built-in async io support for high concurrency w/o
multi-threading. Using python because that's what I know best. :)

### Package Index Format

We need a map of package: dependencies. We also need a map of package:
dependants in order to avoid searching the entire index during a REMOVE
command.

### Package Index Storage

This is where it gets interesting! So many options, so little time...

#### Memory (+ Disk)

Store the entire forward and reverse index in memory. Presumably we want
some durability (i.e. let's not lose the whole index if the server
crashes), so we can't be *only* in memory. Python doesn't have built-in
async file io support, but we could do writes to disk in another thread
so we don't block the event loop.

Can we even store everything in memory? There are about 30 thousand
packages in the apt index. If we have about that many entries and each
entry is 100 bytes average (for the sake of argument), we can store the
entire forward and reverse index in 6MB of RAM. Even if our napkin math
is off by an order of magnitude, we can still do it without breaking a
sweat.

Pros:

- Fast. All client command operations are constant time since we
  have maps in memory. Serialization to disk would be slow but we don't
  care since we offload the writes to another thread.
- Simple to implement

Cons:

- Doesn't scale horizontally since the data wouldn't be shared

#### Shared Disk

Store the index on disk and use NFS (or GlusterFS, or a shared Docker
volume, etc) to share the data among the index servers. Rely on storage
infrastructure to provide disk redundancy.

Pros:

- Horizontally scalable
- Removes single point of failure

Cons:

- Slower than the in-memory solution. We'll be going over the network
  for writes, and to (indirectly) check file attributes before reading.
  Assuming that reads will far outnumber writes, however, the local
  kernel page cache will save us from reading index data over the
  network most of the time.
- Slightly more complex than in-memory solution. We need to worry about
  two index servers trying to write the same file at the same time. We
  also need to consider the best way in which to partition the index
  data into files.

##### Index Partitioning Scheme

So what's the best way to split the index data into files?

- One forward index file, one reverse index file. Simple to implement,
  but suffers from other problems. Every write would invalidate the
  entire locally-cached file, which would be terrible for performance. We
  also need to search the entire index for every read, or incur the
  overhead of deserializing to a structured format for every read.
- One forward and reverse index file for each package in the index.
  Simple to implement. Writes only invalidate data for the affected
  packages. Don't have to search the data as each file contains only the
  data for one package. We'll have thousands of small files, but ext4
  can handle it (although we may want to partition into a/ b/ c/ ... etc
  subdirs for administrator sanity). Many small files has potential to
  waste page cache space - if we have every index file in the cache at
  the same time, that's ~240MB, which is far greater than the actual
  size of the index. This is probably an acceptable trade-off for the
  design simplicity.
- A hybrid approach where we have multiple index files containing data
  for multiple packages (probably divided up lexicographically). We'd
  potentially waste less memory, but cache invalidations would increase
  and we'd need to search through a subset of the index data for each
  read. The added complexity of implementation doesn't seem worth it.

#### 3rd-party Data Store

In Real Life we might use an off-the-shelf transactional, redundant
data store like Redis Cluster or Postgres, especially if we're already
using them elsewhere in our infrastructure.

## Design Choices

We'll implement the Shared Disk approach, partitioning the forward and
reverse index data into one file per package. This approach seems to offer
the best balance of scalability, reliability, performance, and
simplicity/maintainability.

We should implement our indexing scheme in a such a way that it could
easily be swapped out for another approach so that we can easily try
other implementations if we want to.
