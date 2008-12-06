# -*- coding: utf-8 -*-

#Canto - ncurses RSS reader
#   Copyright (C) 2008 Jack Miller <jack@codezen.org>
#
#   This program is free software; you can redistribute it and/or modify
#   it under the terms of the GNU General Public License version 2 as 
#   published by the Free Software Foundation.

import story
import tag

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

class Feed(tag.Tag):
    def __init__(self, cfg, dirpath, t, URL, rate, keep, renderer, filterlist,
            sort, username, password):

        if t:
            tag.Tag.__init__(self, sort, t)
        else:
            self.tag = None

        self.ufp = None
        self.sorts = sort
        self.path = dirpath
        self.URL = URL
        self.cfg = cfg
        self.renderer = renderer
        self.rate = rate
        self.time = 1
        self.keep = keep
        self.changed = 0
        self.filterlist = filterlist
        self.filter_idx = 0
        self.username = username
        self.password = password
    
    def update(self):
        lockflags = fcntl.LOCK_SH
        if self.tag:
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

        if not self.tag:
            if "feed" in self.ufp and "title" in self.ufp["feed"]:
                tag.Tag.__init__(self, self.sorts, self.ufp["feed"]["title"])
            else:
                # Using URL for tag, no guarantees
                tag.Tag.__init__(self, self.sorts, self.URL)

        self.__do_extend()
        return 1

    # __do_extend creates a Story() object out of each of the
    # ["entries"] in the UFP item. It's important to note that
    # .extend is overridden by Tag() which Feed() inherits from.

    def __do_extend(self):
        self.clear()

        # This happens if the feed name was changed.
        for entry in self.ufp["entries"]:
            if entry["canto_state"][0] != self.tag:
                entry["canto_state"][0] = self.tag

        if self.filterlist[self.filter_idx]:
            self.extend(filter(\
                    lambda x: self.filterlist[self.filter_idx](self,x),\
                    [story.Story(entry, self, self.renderer)\
                    for entry in self.ufp["entries"]]))
        else:
            self.extend(\
                    [story.Story(entry, self, self.renderer) \
                    for entry in self.ufp["entries"]])

    def next_filter(self):
        if self.filter_idx < len(self.filterlist) - 1:
            self.filter_idx += 1
            self.__do_extend()
            return 1
        return 0

    def prev_filter(self):
        if self.filter_idx > 0:
            self.filter_idx -= 1
            self.__do_extend()
            return 1
        return 0

    def has_changed(self):
        self.changed = 1

    def todisk(self):
        f = open(self.path, "r+")
        try:
            fcntl.flock(f.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            f.truncate()
            cPickle.dump(self.ufp, f)
        except:
            return 0
        finally:
            fcntl.flock(f.fileno(), fcntl.LOCK_UN)
            f.close()

        self.changed = 0
        return 1

    def tick(self):
        if self.changed:
            self.todisk()

        self.time -= 1
        if self.time <= 0:
            if not self.update() or len(self) == 0 :
                self.time = 1
            else:
                self.time = self.rate
