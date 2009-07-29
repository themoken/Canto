# -*- coding: utf-8 -*-

#Canto - ncurses RSS reader
#   Copyright (C) 2008 Jack Miller <jack@codezen.org>
#
#   This program is free software; you can redistribute it and/or modify
#   it under the terms of the GNU General Public License version 2 as 
#   published by the Free Software Foundation.

# Processes are used for concurrency in canto because Python's GIL makes threads
# worthlessly slow. The initial thread based reimplementation of canto for 0.7.x
# made strides towards responsiveness, but the speed was agonizing in some
# cases, and after reading http://www.dabeaz.com/python/GIL.pdf, it was clear
# that they weren't working as well as you would anticipate.
#
# --SIDE RANT--
# I know that GvR has stated that the GIL isn't going anywhere
# anytime soon. I think this is the worst choice possible for Python. When it
# was initially implemented in the 90s, multi-processor, multi-core machines
# were basically *unheard of* outside of corporate computing. These days you
# can't buy a processor without getting multiple cores and sacrificing
# concurrent performance for single threaded performance is a huge mistake. In
# the future, languages that support massive parallelism are going to clean
# Python's clock (see: Haskell, Erlang).
# --END SIDE RANT--
#
# Multiprocessing in canto is not simple. The ProcessManager class forks a
# process with two pipes, one directed to the process and another directed from
# the process (the typical pipe setup). The interface process puts a work object
# in the pipe, the worker process does the work and puts the result in the
# outgoing pipe. The work tuples looke like this:
#
#       (action, arguments...)
#
# There are a number of actions:
#   (PROC_UPDATE, URL, old items)
#      performs on disk update only, this is used early in init when we're
#      trying to rectify tags from ondisk content
#
#   (PROC_GETTAGS, )
#      requests that the process return the rectified tags (i.e. collisions
#      resolved)
#
#   (PROC_FILTER / PROCESS_BOTH , URL, old items, global filter index,
#    [tag_info], refilter)
#      performs the filtering/sorting (in addition to update for BOTH) this is
#      the most common full update. PROC_FILTER is only used after PROC_UPDATE
#      early on. [tag_info] is a list of one tuple per tag containing:
#
#         (tag string, tag filter index, tag sort index)
#
#   (PROC_FLUSH, )
#      This essentially serves as a marker in the pipe that's returned verbatim
#      when the worker thread receives it. In practice, the ProcessHandler's
#      flush() call puts it into the pipe and discards any output until it gets
#      it back. This is used when the items in the pipe are no longer accurate
#      (i.e. the filter/sort/tag settings have changed.
#
#   (PROC_SYNC, URL, old items)
#      This syncs the state to disk. Typically the state is saved on update, but
#      on exiting the program, it needs to be explicitly synced to disk so that
#      any state changes made between the last disk update are saved.
#
#   (PROC_KILL, )
#      Kills the process. In implementation, it's just PROC_FLUSH with an added
#      clause so it terminates after returning the same tuple. After that tuple
#      if received back, it's guaranteed that the process was safely exited and
#      it can be assumed that the pipes are no longer active.

# Most of the return tuples are self-explanatory. The most common return from
# PROC_BOTH looks like this:
#
#       (URL, stories, newdiff, olddiff)
#
# Where both diffs are arrays that match up with all of the currently used tags.
# For each tag, the diff contains
#
#       (global filter index, tag filter index, tag sort index, new/old item
#           indices)
#
# This diff includes information to keep everything in sync. While the thread
# works the filters and sorts can change so when the interface thread receives
# the diff info it has to check that it's still valid.

# If it is valid, items are added or evicted from the tags.

# NOTE: If this doesn't make sense, canto.gui.alarm() is where this format is
# unravelled.

# WHY ALL THE INDICES? Since we're already passing everything but the kitchen
# sink explicitly through the pipes, it might seem odd to pass index numbers
# back and forth. However, passing lambdas or functions through pipes is not
# easily possible because they are unpickle-able. The solution is that after the
# os.fork(), the all_filters and all_sorts list (in addition to the empty Feed
# objects) are still resident in the new process' memory. So we pass indices
# into those lists to workaround the inability to pass the functions themselves.

# An unfortunate side-effect is that all filters and sorts have to be known at
# the time of the os.fork since the lists won't be synchronized between
# processes automatically (which is one reason processes are more difficult to
# work with than threads).

# The point here is to make the interface process have to do the absolute
# minimum because every second spent updating is a second spent unresponsive to
# the user.

from const import *

import time
import sys
import os

try:
    from multiprocessing import Process, Queue
except Exception, e:
    try:
        from processing import Process, Queue
    except:
        print "Canto 0.7.x requires the python-processing module"+\
              " to run on Python 2.5"
        sys.exit(-1)

class ProcessHandler():
    def __init__(self, cfg):
        self.cfg = cfg
        self.start_process(cfg)

    def start_process(self, cfg):
        self.updated = Queue()
        self.update = Queue()
        self.process = \
                Process(target = self.run,
                        args = (self.update, self.updated,
                            cfg.all_filters, cfg.all_sorts, cfg.feeds))

        try:
            self.process.start()
        except OSError:
            pass

    def run(self, update, updated, all_filters, all_sorts, feeds):
        def scan_tags(feeds):

            # This chunk of code takes any base tags that inadvertantly conflict
            # (i.e. weren't explicitly set by the user) and resolves them into 
            # Tag, Tag (2), Tag (3), etc.

            # This may seem like paranoia, but half-assed feed generators that 
            # use default feed titles shouldn't break Canto.

            base_tags = {}
            for f in [x for x in feeds if x.base_set and\
                    not x.base_explicit]:
                otag = f.tags[0]
                if f.tags[0] in base_tags:
                    base_tags[otag] += 1

                    # We check each tag is unique, even if we're
                    # generating a new one so that if a user defines
                    # "Tag, Tag, Tag (2)", it resolves to
                    # "Tag, Tag (3), Tag (2)"

                    while f.tags[0] + (" (%d)" % base_tags[otag]) in base_tags:
                        base_tags[otag] += 1
                    f.tags[0] += " (%d)" % base_tags[otag]

                    # Remove original tag from all stories in the feed
                    for s in f:
                        s.unset(otag)
                        s.set(f.tags[0])
                else:
                    base_tags[f.tags[0]] = 1


        def send(obj):
            return updated.put(obj)

        while True:
            while True:
                try:
                    r = update.get(True, 0.1)
                except:
                    # If parent canto is dead, kill ourselves
                    if os.getppid() == 1:
                        r = (PROC_KILL, )
                        send = lambda x: True
                        break
                    continue
                break

            action, args = r[0],r[1:]

            if action == PROC_GETTAGS:
                scan_tags(feeds)
                send([ f.tags for f in feeds ])
                continue
            if action in [PROC_FLUSH, PROC_KILL]:
                # Make sure we leave the on-disk presence constant
                send((action, ))
                if action == PROC_KILL:
                    update.close()
                    updated.close()
                    sys.exit(0)
                continue
            if action == PROC_SYNC:
                feed = [ f for f in feeds if f.URL == args[0] ][0]
                feed.merge(args[1])
                while feed.changed():
                    feed.todisk()
                send((PROC_SYNC,))
                continue

            # PROC_UPDATE, just load the data from disk.
            if action >= PROC_UPDATE:
                feed = [ f for f in feeds if f.URL == args[0] ][0]
                feed.merge(args[1])
                if not feed.update():
                    continue

            if action == PROC_UPDATE:
                send((action, feed[:]))
            else:
                prev = args[1]
                filter = args[2]
                taginfo = args[3]
                refilter = args[4]

                if refilter:
                    prev = []

                # Step 1: Global Filters

                gf = all_filters[filter]
                new = []
                for item in feed:
                    if (item in prev) or (gf and (not gf(feed, item))):
                        continue
                    new.append(item)

                old = []
                for item in prev:
                    if (item in feed) and ((not gf) or gf(feed, item)):
                        continue
                    old.append(item)

                # Step 2: Tag filters, initial diff
                ndiff = [None] * len(taginfo)
                for item in new:
                    for i, (t, tf, ts) in enumerate(taginfo):
                        tagf = all_filters[tf]
                        if t in item["canto_state"] and\
                                ((not tagf) or tagf(t,item)):
                            if not ndiff[i]:
                                ndiff[i] = [item]
                            else:
                                ndiff[i].append(item)

                odiff = [None] * len(taginfo)
                for item in old:
                    for i, (t, tf, ts) in enumerate(taginfo):
                        tagf = all_filters[tf]
                        if t in item["canto_state"] and\
                                ((not tagf) or tagf(t, item)):
                            if not odiff[i]:
                                odiff[i] = [item]
                            else:
                                odiff[i].append(item)

                # Step 3: Tag sorts
                for i, (t, tf, ts) in enumerate(taginfo):
                    sort = all_sorts[ts]
                    if not sort:
                        break
                    if ndiff[i]:
                        ndiff[i].sort(sort)
                    if odiff[i]:
                        odiff[i].sort(sort)

                # Step 4: Convert items into indices
                for newdiff in ndiff:
                    if not newdiff:
                        continue
                    for i, item in enumerate(newdiff):
                        newdiff[i] = feed.index(newdiff[i])

                for olddiff in odiff:
                    if not olddiff:
                        continue
                    for i, item in enumerate(olddiff):
                        olddiff[i] = prev.index(olddiff[i])

                # Step 5: Add parity information
                for i, (t, tf, ts) in enumerate(taginfo):
                    ndiff[i] = (filter, tf, ts, ndiff[i])
                    odiff[i] = (filter, tf, ts, odiff[i])

                # Step 6: Queue up the results for the interface process.
                send((feed.URL, feed[:], ndiff, odiff))

            if action > PROC_UPDATE:
                del feed[:]

    def send(self, obj):
        return self.update.put(obj)

    def recv(self, block=True, timeout=None):
        r = None
        try:
            r = self.updated.get(block, timeout)
        except:
            pass
        return r

    def send_and_wait(self, symbol):
        self.send((symbol, ))
        while True:
            got = self.recv()
            if got == (symbol, ):
                return

    def kill_process(self):
        self.send_and_wait(PROC_KILL)
        self.update.close()
        self.updated.close()

        # OSX seems to not like the process join.
        # We shouldn't care, since it should be dead
        # by now anyway.
        try:
            self.process.join()
        except:
            pass

    def flush(self):
        self.send_and_wait(PROC_FLUSH)

    def sync(self):
        for f in self.cfg.feeds:
            self.send((PROC_SYNC, f.URL, f[:]))
            self.recv()
