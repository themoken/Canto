# -*- coding: utf-8 -*-

#Canto - ncurses RSS reader
#   Copyright (C) 2008 Jack Miller <jack@codezen.org>
#
#   This program is free software; you can redistribute it and/or modify
#   it under the terms of the GNU General Public License version 2 as 
#   published by the Free Software Foundation.

class Tag(list):
    def __init__(self, c = "*"):
        list.__init__(self)
        self.tag = c
        self.collapsed = 0
        self.start = 0
        self.read = 0
        self.unread = 0

    def search_stories(self, story):
        for i in range(len(self)) :
            if self[i] == story :
                return i
        return -1

    def all_read(self):
        for s in self : s.read()
        self.unread = 0
        self.read = len(self)

    def all_unread(self):
        for s in self : s.unread()
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
        list.extend(self, [s for s in iter if self.tag in s["tags"]])
        self.read = len(filter(lambda x : x.wasread(), self))
        self.unread = len(self) - self.read

    def clear(self):
        while len(self) : self.pop()
