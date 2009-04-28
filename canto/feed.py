# -*- coding: utf-8 -*-

#Canto - ncurses RSS reader
#   Copyright (C) 2008 Jack Miller <jack@codezen.org>
#
#   This program is free software; you can redistribute it and/or modify
#   it under the terms of the GNU General Public License version 2 as 
#   published by the Free Software Foundation.

from const import VERSION_TUPLE
import story
import tag

from threading import Thread
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
        self.ufp = []
   
    def update(self):
        lockflags = fcntl.LOCK_SH
        if self.base_set:
            lockflags |= fcntl.LOCK_NB

        try:
            f = open(self.path, "r")
            try:
                fcntl.flock(f.fileno(), lockflags)
                self.ufp = cPickle.load(f)
            except:
                return 0
            finally:
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)
                f.close()
        except:
            return 0

        # If this data pre-dates 0.6.0 (the last disk format update)
        # toss a key error.
        if "canto_version" not in self.ufp or\
                self.ufp["canto_version"][1] < 6:
            raise KeyError

        if not self.base_set:
            self.base_set = 1
            if "feed" in self.ufp and "title" in self.ufp["feed"]:
                replace = lambda x: x or self.ufp["feed"]["title"]
                self.tags = [ replace(x) for x in self.tags]
            else:
                # Using URL for tag, no guarantees
                self.tags = [self.URL] + self.tags

        self.extend(self.ufp["entries"])
        self.todisk()
        return 1

    def extend(self, entries):
        newlist = []
        for entry in entries:
            # If tags were added in the configuration, c-f won't
            # notice (doesn't care about tags), so we check and
            # append as needed.

            for tag in self.tags:
                if tag not in entry["canto_state"]:
                    entry["canto_state"].append(tag)

            for centry in self:
                if centry["id"] == entry["id"]:
                    if entry["canto_state"] != centry["canto_state"]:
                        if centry.updated:
                            entry["canto_state"] = centry["canto_state"]
                        else:
                            centry["canto_state"] = entry["canto_state"]
                    break
            else:
                newlist.append(story.Story(entry))

        for centry in self:
            if centry not in entries:
                self.remove(centry)

        list.extend(self, filter(self.filter, newlist))

    def todisk(self):
        changed = self.changed()
        if not changed :
            return

        f = open(self.path, "r+")
        try:
            fcntl.flock(f.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            f.seek(0, 0)
            f.truncate()
            cPickle.dump(self.ufp, f)
            f.flush()
            for x in changed:
                x.updated = 0
        except:
            return 0
        finally:
            fcntl.flock(f.fileno(), fcntl.LOCK_UN)
            f.close()
        return 1

    def changed(self):
        return [ x for x in self if x.updated ]

class UpdateThread(Thread):
    def __init__(self, feed):
        self.feed = feed
        self.new = []
        self.alive = 1

    def run(self, old, filter):
        if self.feed.update():
            self.feed.time = self.feed.rate

        if not filter:
            filter = lambda x, y: 1

        self.new = []
        for item in self.feed:
            if item in old:
                continue
            if not filter(self.feed, item):
                continue
            self.new.append(item)

        self.old = []
        for item in old:
            if item in self.feed:
                continue
            if filter(self.feed, item):
                continue
            self.old.append(item)

        self.alive = 0
