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

class Feed(tag.Tag):
    def __init__(self, cfg, dirpath, t, URL, rate, keep, renderer, filterlist):
        tag.Tag.__init__(self, t)
        self.ufp = None

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
    
    def lock(self):
        try:
            f = os.open(self.lpath, os.O_CREAT|os.O_EXCL)
            os.close(f)
        except OSError:
            return 0
        return 1

    def unlock(self):
        os.unlink(self.lpath)

    def update(self):
        if not self.lock():
            return 0
        f = open(self.path, "rb")
        self.ufp = cPickle.load(f)
        f.close()
        self.unlock()
        self.__do_extend()
        return 1

    def __do_extend(self):
        self.clear()
        self.extend(filter(self.filterlist[self.filter_idx],\
                [story.Story(entry, self, self.renderer)\
                for entry in self.ufp["entries"]]))

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
