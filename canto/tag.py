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
    def __init__(self, cfg, renderer, sorts = [[None]], \
            filters = [None], c = "*"):

        list.__init__(self)

        self.cfg = cfg
        self.renderer = renderer
        self.tag = c
        self.collapsed = 0
        self.start = 0
        self.read = 0
        self.unread = 0

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
            s.set("read")
        self.unread = 0
        self.read = len(self)

    def all_unread(self):
        for s in self :
            s.unset("read")
        self.read = 0
        self.unread = len(self)

    def set_read(self, item):
        if not item.was("read"):
            item.set("read")
            self.unread -= 1
            self.read += 1

    def set_unread(self, item):
        if item.was("read"):
            item.unset("read")
            self.unread += 1
            self.read -= 1

    def retract(self, iter):
        for item in iter:
            if item in self:
                if item.was("read"):
                    self.read -= 1
                else:
                    self.unread -= 1
                self.remove(item)
        self.enum()

    def extend(self, iter):
        filt = self.filters.cur()
        if filt:
            list.extend(self, filter(lambda x: filt(self, x), iter))
        else:
            list.extend(self, iter)

        empty = 0
        if filt and not len(self):
            d = { "title" : "No unfiltered items.",
                  "description" : "You've filtered out everything!",
                  "canto_state" : [self.tag, "unread"],
                  "id" : None
                }

            stub = story.Story(d)
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
        self.enum(empty)

    def enum(self, empty = 0):
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

            self.read = len(filter(lambda x : x.was("read"), self))
            self.unread = len(self) - self.read

    def clear(self):
        del self[:]
