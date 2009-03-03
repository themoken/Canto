# -*- coding: utf-8 -*-

#Canto - ncurses RSS reader
#   Copyright (C) 2008 Jack Miller <jack@codezen.org>
#
#   This program is free software; you can redistribute it and/or modify
#   it under the terms of the GNU General Public License version 2 as 
#   published by the Free Software Foundation.

from utility import Cycle
import story

class Tag(list):
    def __init__(self, cfg, sorts = [[None]], filters = [None], c = "*"):
        list.__init__(self)
        self.cfg = cfg
        self.tag = c
        self.collapsed = 0
        self.start = 0
        self.read = 0
        self.unread = 0
        self.last_iter = []

        self.filters = filters
        self.sorts = sorts

    def __eq__(self, other):
        return self.tag == other.tag

    def __str__(self):
        return self.tag

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

    def extend(self, iter):
        self.last_iter = iter
        matched_tag = [s for s in iter if self.tag in s["canto_state"]]

        filt = self.filters.cur()
        if filt:
            list.extend(self, filter(lambda x: filt(self, x), matched_tag))
        else:
            list.extend(self, matched_tag)

        empty = 0
        if filt and not len(self):
            d = { "title" : "No unfiltered items.",
                  "description" : "You've filtered out everything!",
                  "canto_state" : [self.tag, "unread"],
                  "id" : None
                }

            stub = story.Story(d , None, self.cfg.default_renderer)
            self.append(stub)
            empty = 1
        else:
            if not hasattr(self.sorts.cur(), "__iter__"):
                dosorts = [self.sorts.cur()]
            else:
                dosorts = self.sorts.cur()

            for s in dosorts:
                if s:
                    list.sort(self, s)

        if empty:
            self.read = 0
            self.unread = 0
            self[0].idx = 0
            self[0].last = 1
        else:
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
