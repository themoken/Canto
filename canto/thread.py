# -*- coding: utf-8 -*-

#Canto - ncurses RSS reader
#   Copyright (C) 2008 Jack Miller <jack@codezen.org>
#
#   This program is free software; you can redistribute it and/or modify
#   it under the terms of the GNU General Public License version 2 as 
#   published by the Free Software Foundation.

# Threading in canto is not simple. The ThreadManager class spawns two QueueLists
# (more about those below). The main loop (canto.py) puts tuples into the update
# QueueList. Those tuples look like this

#       (cfg, feed, old items, stage)

# The work thread processes based on this input and then puts another tuple on
# the updated QueueList. That tuple looks like this:

#       (newdiff, olddiff)

# Where both diffs are arrays that match up with all of the currently used tags.
# For each tag, the diff contains

#       (global filter, tag filter, tag sort, new/old items)

# This diff includes information to keep everything in sync. While the thread
# works the filters and sorts can change so when the interface thread receives
# the diff info it has to check that it's still valid.

# If it is valid, items are added or evicted from the tags.

# NOTE: If this doesn't make sense, canto.gui.alarm() is where this format is
# unravelled.

# The worker thread has to do a lot. First it performs an update from disk. Then
# it filters those items with the global filters. After that it creates a diff
# for each tag respecting each tag's filters and sorts. Because each diff is
# sorted with the tag's sorts, whenever it adds the items it's a linear time
# list merge with no sorting required.

# The point here is to make the interface thread have to do the absolute
# minimum because every second spent updating is a second spent unresponsive to
# the user.

from const import THREAD_UPDATE, THREAD_FILTER
from threading import Thread, Lock

import time

# The QueueList class differs from the builtin Queue:

# * If an item is already on the Queue, it's not put on again.
# * Items can be rushed to the front of the Queue (could be achieved by a
#   PriorityQueue)
# * It's extremely simple to flush the queue without getting and task_done'ing
#   each item

class QueueList():
    def __init__(self):
        # The queue
        self.iter = []
        self.lock = Lock()

        # Work is a differentiated from items on the Queue. When there are no
        # left on the Queue, work can still be done. This is important because
        # the join() method should wait until there's no work, where empty()
        # returns whether there are more items...
        self.work = 0

    def put(self, obj):
        self.lock.acquire()
        if obj not in self.iter:
            self.iter.insert(0, obj)
            self.work += 1
        self.lock.release()

    # Put to the front of the QueueList
    def put_next(self, obj):
        self.lock.acquire()
        if obj in self.iter:
            self.iter.remove(obj)
        self.iter.append(obj)
        self.work += 1
        self.lock.release()

    def get(self):
        r = None
        self.lock.acquire()
        if len(self.iter):
            r = self.iter.pop(-1)
        self.lock.release()
        return r

    def join(self):
        # Don't pin the CPU
        while self.work: time.sleep(0.1)

    def empty(self):
        self.lock.acquire()
        r = len(self.iter) == 0
        self.lock.release()
        return r

    def flush(self):
        self.lock.acquire()
        self.iter = []
        self.work = 0
        self.lock.release()

    def task_done(self):
        self.lock.acquire()
        self.work -= 1
        self.lock.release()

class ThreadHandler():
    def __init__(self):
        self.update = QueueList()
        self.updated = QueueList()
        self.kill_me = 0
        self.start_thread()

    def work(self):
        while True:
            if self.kill_me:
                return

            # Get the next item
            r = self.update.get()
            if r:
                cfg, feed, prev, do_filter = r
            else:
                # Don't pin the CPU
                time.sleep(0.1)
                continue

            # THREAD_UPDATE, just load the data from disk.
            if do_filter >= THREAD_UPDATE:
                if feed.update():
                    feed.time = feed.rate
                else:
                    continue

            if do_filter >= THREAD_FILTER:
                # Step 1: Global Filters
                filter = cfg.filters.cur()
                nofilt = lambda x, y: 1
                if not filter:
                    filter = nofilt

                new = []
                for item in feed:
                    if item in prev or (not filter(feed, item)):
                        continue
                    new.append(item)

                old = []
                for item in prev:
                    if item in feed and filter(feed, item):
                        continue
                    old.append(item)

                # Step 2: Tag filters, initial diff
                tags = [(t, t.filters.cur() or nofilt)\
                        for t in cfg.tags.cur() ]
                ndiff = [None] * len(tags)
                for item in new:
                    for i, (t, ff) in enumerate(tags):
                        if t.tag in item["canto_state"] and ff(t, item):
                            if not ndiff[i]:
                                ndiff[i] = [item]
                            else:
                                ndiff[i].append(item)

                odiff = [None] * len(tags)
                for item in old:
                    for i, (t, ff) in enumerate(tags):
                        ffilter = t.filters.cur()
                        if t.tag in item["canto_state"] and ff(t, item):
                            if not odiff[i]:
                                odiff[i] = [item]
                            else:
                                odiff[i].append(item)

                # Step 3: Tag sorts, include parity information
                if filter == nofilt:
                    filter = None
                for i, (t, ff) in enumerate(tags):
                    if ff == nofilt:
                        ff = None
                    sort = t.sorts.cur()
                    if ndiff[i]:
                        ndiff[i].sort(sort)
                        ndiff[i] = (filter, ff, sort, ndiff[i])
                    if odiff[i]:
                        odiff[i].sort(sort)
                        odiff[i] = (filter, ff, sort, odiff[i])

                # Step 4: Queue up the results for the interface thread.
                if not self.kill_me:
                    self.updated.put((ndiff, odiff))

            self.update.task_done()

    def start_thread(self):
        self.kill_me = False
        self.thread = Thread(target=self.work)
        self.thread.daemon = True
        self.thread.start()

    def kill_thread(self):
        self.kill_me = True

    def flush(self, restart = 1):
        self.kill_thread()
        self.update.flush()
        while self.thread.isAlive(): pass

        # No updates currently happening, updated won't be touched again.

        self.updated.flush()
        if restart:
            self.start_thread()
