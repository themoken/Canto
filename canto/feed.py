# -*- coding: utf-8 -*-

#Canto - ncurses RSS reader
#   Copyright (C) 2008 Jack Miller <jack@codezen.org>
#
#   This program is free software; you can redistribute it and/or modify
#   it under the terms of the GNU General Public License version 2 as 
#   published by the Free Software Foundation.

import sys
import story
import utility
import interface_draw
import re
import codecs
import tag
import os
import cPickle

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
            sort):

        if t:
            tag.Tag.__init__(self, sort, t)
        else:
            self.tag = None

        self.ufp = None
        self.sorts = sort
        self.path = dirpath
        self.lpath = dirpath + ".lock"
        self.URL = URL
        self.cfg = cfg
        self.renderer = renderer
        self.rate = rate
        self.time = 1
        self.keep = keep
        self.changed = 0
        self.filterlist = filterlist
        self.filter_idx = 0
    
    # Simple traditional Unix file lock.
    def lock(self):
        try:
            f = os.open(self.lpath, os.O_CREAT|os.O_EXCL)
            os.close(f)
        except:
            return 0
        return 1

    def unlock(self):
        os.unlink(self.lpath)

    def update(self):
        if not self.lock():
            return 0

        try:
            f = open(self.path, "rb")
            self.ufp = cPickle.load(f)
            f.close()
        except:
            return 0
        finally:
            self.unlock()

        if not self.tag:
            tag.Tag.__init__(self, self.sorts, self.ufp["feed"]["title"])

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
        if not self.lock():
            return 0

        f = open(self.path, "wb")
        cPickle.dump(self.ufp, f)
        f.close()
        self.changed = 0

        self.unlock()
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
