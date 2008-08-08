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

class Feed(tag.Tag):
    """Feed() encapsulates a feed directory and handles
    all updates in that feed directory when ticked()"""

    def __init__(self, cfg, dirpath, t, URL, rate, keep, title_key):
        tag.Tag.__init__(self, t)
        self.path = dirpath
        self.safetag = self.tag.replace("/", " ")
        self.URL = URL
        self.cfg = cfg
        self.title_key = title_key

        if self.path :
            self.update()

        self.rate = rate
        self.time = 1
        self.keep = keep
        
    def update(self):
        """Invoke an update, reading all of the stories
        from the disk."""

        newlist = []
        try:
            fsock = codecs.open(self.path + "/../" + self.safetag + ".idx", "r", "UTF-8", "ignore")
            try:
                data = fsock.read().split("\00")[:-1]
            finally:
                fsock.close()

            for item in data:
                path = self.path + "/" + item.replace("/", " ")
                s = story.Story(path)
                if not self.title_key or s["title"] not in [x["title"] for x in newlist]:
                    newlist.append(s)

        except IOError:
            pass

        for i in range(len(newlist)):
            r = self.search_stories(newlist[i])
            if r != -1 :
                newlist[i] = self[r]
        
        for i in range(len(self)):
            self.pop()
        self.extend(newlist)

    def tick(self):
        self.time -= 1
        if self.time <= 0:
            self.update()
            if len(self) == 0 :
                self.time = 1
            else:
                self.time = self.rate

    def delete(self):
        try:
            os.unlink(self.path + "/../" + self.safetag + ".idx")
        except:
            pass

        try:
            for i in os.listdir(self.path):
                os.unlink(self.path + "/" + i)
            os.rmdir(self.path)
        except:
            pass
