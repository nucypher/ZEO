=============================================================================
Experiments toward designing a ZEO replacement that servers strings and files
=============================================================================

The goal is a server that is simpler and faster than the current ZEO
server, probably written in a language other than Python.

- Database data are opaque strings. They may be pickles, JSON,
  protocol buffers, whatever, but they are opaque to the server.

- There are still transactions, tids and object ids.

- Server provides packing, but not garbage collection. (It can't do GC
  because data are opaque.) External applications perform GC.

- Pluggable storage.

- Client replication model, invalidation messages are sent when data
  are updated.

- Server replication (similar to ZRS).

For now, we're just exploring options for records and network
protocols and replication languages.

Problem
=======

ZODB shootout and other experiements [#zcperf]_ show that ZEO is way too slow to
serve data.  This is a major impediment to ZODB adoption.

Focus for now is on speeding network performance.  Basically, we want
to speed the processing of server requests.

(Note that another important performance bottleneck for
write-intensive applications are the transaction-management
alogorithms. This too deserves attention, but we think it's orthogonal
to network performance.)




.. [#zcperf] A few years ago we did a lot of work to speed up ZEO
   performance at ZC.  At the time, we thought the biggest issue was
   disk access, but it got a lot more complicated than that.  Out
   tests involved on the order of 50-100 clients. After
   lots of testing, we found that:

   - Disk access was a significant bottleneck with traditional disks.

     - We were able to get ~4X speedup by using SSDs.

     - We were also able to get a signoficant speedup by using
       multiple threads for reading data.

       For the magnetic disks we were using at the time, with multiple
       spindles, the greatest benefit was that we could drive multiple
       spindles on reads.

       The benefit was likely much smaller for SSDs, but there was
       probably some benefit in pushing signficant computation outside
       the GIL.

   - We noticed by looking at strace data that were were also
     spending a significant time waiting for IO, even though we were
     using non-blocking IO.  We ended up switching to a more threaded
     IO model with a thread per client, but still using asyncronous IO
     for each client.

     Using threads for both client communication and reading files,
     together with some minor protocol optimizations allowed us to get
     a 3-4X speedup in ut tests.

     On an 8-processor server we were able to push our server
     processes above 200% CPU, despite the GIL.

   Despite the fact that we were using very fast (FusionIO) SSDs and a
   Gigabit network, we couldn't get our average read-request service
   times below 3ms under heavy load. This is still way too slow.  We
   should be able to do much better than that.

   Our theory is that we've hit a wall in terms of how fast we can
   server this data with Python.

   Since then, we've done (mostly) unrelated experiements serving
   files with Python-based web servers. Using a simpler file server
   written using gevent and bobo, we've been able to achive
   throughputs of several thousand requests per second.

   ZEO servers are quite a bit more complicated than simple file
   servers. Because data are being updated, there are a fair number of
   locking operations, which are expensive. Possibly a different
   locking stategy could achiev a lot.

Plan
====

Compare protocol buffers and pickle for network protocol
--------------------------------------------------------

Protocol buffers provide language independence. Is there a price to
pay (or a win)?

Python-based string server
--------------------------

Implement a simple string server

- reads and writes, and invalidations

- Partial file-storage2 implementation for storing data.

- Protocol-buffers-based network protocol.

- asyncio-based implementation

- Review locking strategies to reduce lock operations.

  Current FileStorage file-pool locking is too low-level. We get write
  lock and prevent reads on oids that aren't being written.

- OID level commit locks.

  - Allow unfettered reading of unlocked oids.

  - Allow multiple transactions in second phase of 2pc if they are
    writing separe OIDs.


Python-based client and test infrastructure
-------------------------------------------

- asyncio and multi-processor based.

  Very simple. Read-only.

- AWS

  - Use machines large enough to avoid steel.

  - Storage server with lots of ram, processors and fast SSD EBS
    volumns

  - Client machines with fast IO.

Go server implementation
------------------------

Go is pretty fast and can leverage multiple cpus.
