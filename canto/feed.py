# -*- coding: utf-8 -*-

#Canto - ncurses RSS reader
#   Copyright (C) 2008 Jack Miller <jack@codezen.org>
#
#   This program is free software; you can redistribute it and/or modify
#   it under the terms of the GNU General Public License version 2 as 
#   published by the Free Software Foundation.

from const import *
import story
import tag

from threading import Lock
from Queue import Queue
import cPickle
import fcntl

# Feed() controls a single feed and implements all of the update functionality
# on top of Tag() (which is the generic class for lists of items). Feed() is
# also the lowest granule for custom renderers because the renderers are
# most likely using information specific to the XML, rather than information
# specific to an arbitrary list.

# Each feed has a self.ufp item that contains a verbatim copy of the data
# returned by the feedparser.

# Each feed will also only write its status back to disk on tick() and only if
# has_changed() has been called by one of the Story() items Feed() contains.

class Feed(list):
    def __init__(self, cfg, dirpath, URL, tags, rate, keep, \
            filter, username, password):

        # Configuration set settings
        self.tags = tags
        if self.tags[0] == None:
            self.base_set = 0
            self.base_explicit = 0
        else:
            self.base_set = 1
            self.base_explicit = 1

        self.URL = URL
        self.rate = rate
        self.time = 1
        self.keep = keep
        self.username = username
        self.password = password

        # Hard filter
        if filter:
            self.filter = lambda x: filter(self, x)
        else:
            self.filter = None

        # Other necessities
        self.path = dirpath
        self.cfg = cfg

    def get_ufp(self):
        lockflags = fcntl.LOCK_SH
        if self.base_set:
            lockflags |= fcntl.LOCK_NB

        try:
            f = open(self.path, "r")
            try:
                fcntl.flock(f.fileno(), lockflags)
                ufp = cPickle.load(f)
            except:
                return 0
            finally:
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)
                f.close()
        except:
            return 0
        return ufp

    def update(self):
        ufp = self.get_ufp()
        if not ufp:
            return 0

        # If this data pre-dates 0.6.0 (the last disk format update)
        # toss a key error.
        if "canto_version" not in ufp or\
                ufp["canto_version"][1] < 6:
            raise KeyError

        if not self.base_set:
            self.base_set = 1
            if "feed" in ufp and "title" in ufp["feed"]:
                replace = lambda x: x or ufp["feed"]["title"]
                self.tags = [ replace(x) for x in self.tags]
            else:
                # Using URL for tag, no guarantees
                self.tags = [self.URL] + self.tags

        self.extend(ufp["entries"])
        self.todisk(ufp)
        return 1

    def extend(self, entries):
        newlist = []
        for entry in entries:
            # If tags were added in the configuration, c-f won't
            # notice (doesn't care about tags), so we check and
            # append as needed.

            nentry = {}
            nentry["id"] = entry["id"]
            nentry["canto_state"] = entry["canto_state"]
            nentry["title"] = entry["title"]

            if "link" in entry:
                nentry["link"] = entry["link"]
            elif "href" in entry:
                nentry["link"] = entry["href"]

            for tag in self.tags:
                if tag not in nentry["canto_state"]:
                    nentry["canto_state"].append(tag)

            if nentry not in self:
                newlist.append(story.Story(nentry, self.get_ufp))

        for centry in self:
            if centry not in entries:
                self.remove(centry)

        list.extend(self, filter(self.filter, newlist))

    def todisk(self, ufp=None):
        if ufp == None:
            ufp = self.get_ufp()
        if not ufp:
            return
        changed = self.changed()
        if not changed :
            return

        for entry in changed:
            old = ufp["entries"][ufp["entries"].index(entry)]
            if old["canto_state"] != entry["canto_state"]:
               if entry.updated:
                   old["canto_state"] = entry["canto_state"]
               else:
                   entry["canto_state"] = old["canto_state"]

        f = open(self.path, "r+")
        try:
            fcntl.flock(f.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            f.seek(0, 0)
            f.truncate()
            cPickle.dump(ufp, f)
            f.flush()
            for x in changed:
                x.updated = 0
        except:
            return 0
        finally:
            fcntl.flock(f.fileno(), fcntl.LOCK_UN)
            f.close()
        del ufp
        return 1

    def changed(self):
        return [ x for x in self if x.updated ]

update = Queue()
updated = Queue()
ulock = Lock()

def work():
    while True:
        cfg, feed, prev, do_filter = update.get()
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
            ulock.acquire()
            updated.put((ndiff, odiff))
            ulock.release()
        update.task_done()

def flush():
    while not update.empty():
        update.get()
        update.task_done()
    ulock.acquire()
    while not updated.empty():
        updated.get()
        updated.task_done()
    ulock.release()
