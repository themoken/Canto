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
    def __init__(self, cfg, dirpath, t, URL, rate, keep, title_key):
        tag.Tag.__init__(self, t)
        self.ufp = None

        self.path = dirpath
        self.safetag = self.tag.replace("/", " ")
        self.URL = URL
        self.cfg = cfg

        if self.path :
            self.update()

        self.rate = rate
        self.time = 1
        self.keep = keep
        self.changed = 0
    
    def update(self):
        if not os.path.exists(self.path):
            return

        f = open(self.path, "rb")
        self.ufp = cPickle.load(f)
        f.close()

        self.clear()
        for entry in self.ufp["entries"]:
            self.append(story.Story(entry, self.has_changed))

    def has_changed(self):
        self.changed = 1

    def todisk(self):
        f = open(self.path, "wb")
        cPickle.dump(self.ufp, f)
        f.close()

    def tick(self):
        if self.changed:
            self.todisk()
            self.changed = 0

        self.time -= 1
        if self.time <= 0:
            self.update()
            if len(self) == 0 :
                self.time = 1
            else:
                self.time = self.rate
