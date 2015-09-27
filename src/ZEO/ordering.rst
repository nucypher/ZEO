Ordering requirements for serializability
=========================================

To assure serializability, we have to enforce ordering on reads.

From the point of view of a client, every transaction has a start
time.  All data read are current as of just before the start time.
Any data read by the transaction most have been the last data
committed for an OID before the start time.

The start time of a transaction is the TID of the first invalidation
received by a client after the transaction starts. (On transaction
start, any queued invalidations are processed as part of the start up.)
This means that when a transaction starts, the start time is unknown.

The client receives current records and invalidations from the server.
The client must never recieve a current record and an invalidation
record for an oid out of order.

Consider, if a client recieves and invalidation and with a tid TID2
and then a current value with TID1, it will mix T1 data with T2 data
and this show an inconsistent view. Note, however, that the client
could detect this and reject the update, requesting a new update
before T2.

If a client revieves a current value for an OID with TID2 and then an
invalidation for T1, it will invalidate the object, but the object
will be refetched if necessary. Unfortunately, the client may have
done some computation with the TID2 data and thus the computation will
be inconsistent.  The client could abort the transaction in this case.

If a client reads an object at TID2, then reads it at TID1, it will
have processed inconsistent data.  It would presumably get an
invalidation for TID2 eventually.

The client could detect some inconsistencies if it remembered tids
previously read for an object. Ghost remember their previous TIDs, but
ghosts may be garbage collected.

Our standard rules is thet current-object reads must always be
processed in TID order, where current object reads include
invalidations.  We ensure this by:

- using TCP connections, wich preserve ordering,

- always sending messages in order, and

- always processing messages in order.

Sending data in correct order  imposes requirements on the server that
lead to locking.

It's possible that we could relax the ording requirement on the server
if we could detect ordering conflicts on the client and retry. It's
unclear, however, if the savings i relaxing the server ordering
requirements would be cancelled by the cost of conflict handling.










Note, however, that once a 
