##############################################################################
# 
# Zope Public License (ZPL) Version 1.0
# -------------------------------------
# 
# Copyright (c) Digital Creations.  All rights reserved.
# 
# This license has been certified as Open Source(tm).
# 
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are
# met:
# 
# 1. Redistributions in source code must retain the above copyright
#    notice, this list of conditions, and the following disclaimer.
# 
# 2. Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions, and the following disclaimer in
#    the documentation and/or other materials provided with the
#    distribution.
# 
# 3. Digital Creations requests that attribution be given to Zope
#    in any manner possible. Zope includes a "Powered by Zope"
#    button that is installed by default. While it is not a license
#    violation to remove this button, it is requested that the
#    attribution remain. A significant investment has been put
#    into Zope, and this effort will continue if the Zope community
#    continues to grow. This is one way to assure that growth.
# 
# 4. All advertising materials and documentation mentioning
#    features derived from or use of this software must display
#    the following acknowledgement:
# 
#      "This product includes software developed by Digital Creations
#      for use in the Z Object Publishing Environment
#      (http://www.zope.org/)."
# 
#    In the event that the product being advertised includes an
#    intact Zope distribution (with copyright and license included)
#    then this clause is waived.
# 
# 5. Names associated with Zope or Digital Creations must not be used to
#    endorse or promote products derived from this software without
#    prior written permission from Digital Creations.
# 
# 6. Modified redistributions of any form whatsoever must retain
#    the following acknowledgment:
# 
#      "This product includes software developed by Digital Creations
#      for use in the Z Object Publishing Environment
#      (http://www.zope.org/)."
# 
#    Intact (re-)distributions of any official Zope release do not
#    require an external acknowledgement.
# 
# 7. Modifications are encouraged but must be packaged separately as
#    patches to official Zope releases.  Distributions that do not
#    clearly separate the patches from the original work must be clearly
#    labeled as unofficial distributions.  Modifications which do not
#    carry the name Zope may be packaged in any form, as long as they
#    conform to all of the clauses above.
# 
# 
# Disclaimer
# 
#   THIS SOFTWARE IS PROVIDED BY DIGITAL CREATIONS ``AS IS'' AND ANY
#   EXPRESSED OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
#   IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR
#   PURPOSE ARE DISCLAIMED.  IN NO EVENT SHALL DIGITAL CREATIONS OR ITS
#   CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
#   SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
#   LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF
#   USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
#   ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
#   OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT
#   OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF
#   SUCH DAMAGE.
# 
# 
# This software consists of contributions made by Digital Creations and
# many individuals on behalf of Digital Creations.  Specific
# attributions are listed in the accompanying credits file.
# 
##############################################################################

# This module is a simplified version of the select_trigger module
# from Sam Rushing's Medusa server.


import asyncore
#import asynchat

import os
import socket
import string
import thread
    
if os.name == 'posix':

    class trigger (asyncore.file_dispatcher):

        "Wake up a call to select() running in the main thread"

        # This is useful in a context where you are using Medusa's I/O
        # subsystem to deliver data, but the data is generated by another
        # thread.  Normally, if Medusa is in the middle of a call to
        # select(), new output data generated by another thread will have
        # to sit until the call to select() either times out or returns.
        # If the trigger is 'pulled' by another thread, it should immediately
        # generate a READ event on the trigger object, which will force the
        # select() invocation to return.

        # A common use for this facility: letting Medusa manage I/O for a
        # large number of connections; but routing each request through a
        # thread chosen from a fixed-size thread pool.  When a thread is
        # acquired, a transaction is performed, but output data is
        # accumulated into buffers that will be emptied more efficiently
        # by Medusa. [picture a server that can process database queries
        # rapidly, but doesn't want to tie up threads waiting to send data
        # to low-bandwidth connections]

        # The other major feature provided by this class is the ability to
        # move work back into the main thread: if you call pull_trigger()
        # with a thunk argument, when select() wakes up and receives the
        # event it will call your thunk from within that thread.  The main
        # purpose of this is to remove the need to wrap thread locks around
        # Medusa's data structures, which normally do not need them.  [To see
        # why this is true, imagine this scenario: A thread tries to push some
        # new data onto a channel's outgoing data queue at the same time that
        # the main thread is trying to remove some]

        def __init__ (self):
            r, w = os.pipe()
            self.trigger = w
            asyncore.file_dispatcher.__init__ (self, r)
            self.lock = thread.allocate_lock()
            self.thunks = []

        def __repr__ (self):
            return '<select-trigger (pipe) at %x>' % id(self)

        def readable (self):
            return 1

        def writable (self):
            return 0

        def handle_connect (self):
            pass

        def pull_trigger (self, thunk=None):
            # print 'PULL_TRIGGER: ', len(self.thunks)
            if thunk:
                try:
                    self.lock.acquire()
                    self.thunks.append (thunk)
                finally:
                    self.lock.release()
            os.write (self.trigger, 'x')

        def handle_read (self):
            self.recv (8192)
            try:
                self.lock.acquire()
                for thunk in self.thunks:
                    try:
                        thunk()
                    except:
                        nil, t, v, tbinfo = asyncore.compact_traceback()
                        print ('exception in trigger thunk:'
                               ' (%s:%s %s)' % (t, v, tbinfo))
                self.thunks = []
            finally:
                self.lock.release()

else:

    # XXX Should define a base class that has the common methods and
    # then put the platform-specific in a subclass named trigger.

    # win32-safe version

    class trigger (asyncore.dispatcher):

        address = ('127.9.9.9', 19999)

        def __init__ (self):
            a = socket.socket (socket.AF_INET, socket.SOCK_STREAM)
            w = socket.socket (socket.AF_INET, socket.SOCK_STREAM)

            # set TCP_NODELAY to true to avoid buffering
            w.setsockopt(socket.IPPROTO_TCP, 1, 1)

            # tricky: get a pair of connected sockets
            host='127.0.0.1'
            port=19999
            while 1:
                try:
                    self.address=(host, port)
                    a.bind(self.address)
                    break
                except:
                    if port <= 19950:
                        raise 'Bind Error', 'Cannot bind trigger!'
                    port=port - 1
            
            a.listen (1)
            w.setblocking (0)
            try:
                w.connect (self.address)
            except:
                pass
            r, addr = a.accept()
            a.close()
            w.setblocking (1)
            self.trigger = w

            asyncore.dispatcher.__init__ (self, r)
            self.lock = thread.allocate_lock()
            self.thunks = []
            self._trigger_connected = 0

        def __repr__ (self):
            return '<select-trigger (loopback) at %x>' % id(self)

        def readable (self):
            return 1

        def writable (self):
            return 0

        def handle_connect (self):
            pass

        def pull_trigger (self, thunk=None):
            if thunk:
                try:
                    self.lock.acquire()
                    self.thunks.append (thunk)
                finally:
                    self.lock.release()
            self.trigger.send ('x')

        def handle_read (self):
            self.recv (8192)
            try:
                self.lock.acquire()
                for thunk in self.thunks:
                    try:
                        thunk()
                    except:
                        nil, t, v, tbinfo = asyncore.compact_traceback()
                        print ('exception in trigger thunk:'
                               ' (%s:%s %s)' % (t, v, tbinfo))
                self.thunks = []
            finally:
                self.lock.release()
