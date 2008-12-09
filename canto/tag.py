# -*- coding: utf-8 -*-

#Canto - ncurses RSS reader
#   Copyright (C) 2008 Jack Miller <jack@codezen.org>
#
#   This program is free software; you can redistribute it and/or modify
#   it under the terms of the GNU General Public License version 2 as 
#   published by the Free Software Foundation.

import story

class Tag(list):
    def __init__(self, cfg, sort = [None], filterlist = [None], c = "*"):
        list.__init__(self)
        self.cfg = cfg
        self.tag = c
        self.collapsed = 0
        self.start = 0
        self.read = 0
        self.unread = 0
        self.sorts = sort
        self.last_iter = []

        self.filterlist = filterlist
        self.filter_idx = 0
        self.filter_override = None

    def __eq__(self, other):
        return self.tag == other.tag

    def search_stories(self, story):
        for i in range(len(self)) :
            if self[i]["id"] == story["id"]:
                return i
        return -1

    def all_read(self):
        for s in self :
            s.read()
        self.unread = 0
        self.read = len(self)

    def all_unread(self):
        for s in self :
            s.unread()
        self.read = 0
        self.unread = len(self)

    def set_read(self, idx):
        if not self[idx].wasread():
            self[idx].read()
            self.unread -= 1
            self.read += 1

    def set_unread(self, idx):
        if self[idx].wasread():
            self[idx].unread()
            self.unread += 1
            self.read -= 1

    def next_filter(self):
        self.filter_override = None
        if self.filter_idx < len(self.filterlist) - 1:
            self.filter_idx += 1
            return 1
        return 0

    def prev_filter(self):
        self.filter_override = None
        if self.filter_idx > 0:
            self.filter_idx -= 1
            return 1
        return 0

    def extend(self, iter):
        self.last_iter = iter
        matched_tag = [s for s in iter if self.tag in s["canto_state"]]

        filt = self.filter_override or self.filterlist[self.filter_idx]
        if filt:
            list.extend(self, filter(lambda x: filt(self, x), matched_tag))
        else:
            list.extend(self, matched_tag)

        if filt and not len(self):
            d = { "title" : "No unfiltered items.",
                  "description" : "You've filtered out everything!",
                  "canto_state" : [self.tag, "unread"],
                  "id" : None
                }

            stub = story.Story(d , None, self.cfg.default_renderer)
            self.append(stub)
        else:
            for s in self.sorts:
                if s:
                    list.sort(self, s)

        lt = len(self)
        for i in range(lt):
            self[i].idx = i
            self[i].last = 0
        if lt:
            self[-1].last = 1

        self.read = len(filter(lambda x : x.wasread(), self))
        self.unread = len(self) - self.read

    def clear(self):
        del self[:]
