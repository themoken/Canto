# -*- coding: utf-8 -*-

#Canto - ncurses RSS reader
#   Copyright (C) 2008 Jack Miller <jack@codezen.org>
#
#   This program is free software; you can redistribute it and/or modify
#   it under the terms of the GNU General Public License version 2 as 
#   published by the Free Software Foundation.

from threading import Thread, Lock
from const import *

import signal
import time
import os

class QueueList():
    def __init__(self):
        self.iter = []
        self.work = 0
        self.lock = Lock()

    def put(self, obj):
        self.lock.acquire()
        if obj not in self.iter:
            self.iter.insert(0, obj)
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
        while self.work: time.sleep(0.1)

    def empty(self):
        self.lock.acquire()
        r = len(self.iter) == 0
        self.lock.release()
        return r

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

            r = self.update.get()
            if r:
                cfg, feed, prev, do_filter = r
            else:
                time.sleep(0.1)
                continue

            if do_filter != THREAD_FILTER:
                if feed.update():
                    feed.time = feed.rate
                else:
                    continue

            if do_filter >= THREAD_FILTER:
                filter = cfg.filters.cur()
                if not filter:
                    filter = lambda x, y: 1

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

                tags = cfg.tags.cur()
                ndiff = [None] * len(tags)
                for item in new:
                    for i, t in enumerate(tags):
                        if t.tag in item["canto_state"]:
                            if not ndiff[i]:
                                ndiff[i] = [item]
                            else:
                                ndiff[i].append(item)

                odiff = [None] * len(tags)
                for item in old:
                    for i, t in enumerate(tags):
                        if t.tag in item["canto_state"]:
                            if not odiff[i]:
                                odiff[i] = [item]
                            else:
                                odiff[i].append(item)

                for i, t in enumerate(tags):
                    sort = t.sorts.cur()
                    if ndiff[i]:
                        ndiff[i].sort(sort)
                        ndiff[i] = (filter, sort, ndiff[i])
                    if odiff[i]:
                        odiff[i].sort(sort)
                        odiff[i] = (filter, sort, odiff[i])

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
        while not self.update.empty():
            self.update.get()
            self.update.task_done()
        while self.thread.isAlive(): pass
        while not self.updated.empty():
            self.updated.get()
            self.updated.task_done()
        if restart:
            self.start_thread()
