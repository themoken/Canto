# -*- coding: utf-8 -*-

#Canto - ncurses RSS reader
#   Copyright (C) 2008 Jack Miller <jack@codezen.org>
#
#   This program is free software; you can redistribute it and/or modify
#   it under the terms of the GNU General Public License version 2 as 
#   published by the Free Software Foundation.

# Story() controls a single story and is always contained in a feed().
# Like Feed(), it contains a self.ufp variable that holds a verbatim copy of
# the data returned by the UFP. The class then mostly serves as a soft wrapper
# around that data.

# Data that is persistent (everything except being selected) is appended to
# the canto_state key in self.ufp and is written to disk by the Feed() object
# automatically.

class Story():
    def __init__(self, ufp, feed, renderer):
        self.tag_idx = 0
        self.idx = 0
        self.last = 0

        self.row = 0
        self.lines = 0
        
        self.ufp = ufp
        self.feed = feed
        self.sel = 0
        self.renderer = renderer

    def __eq__(self, other):
        if self["id"] != other["id"]:
            return 0
        return 1

    def __getitem__(self, key):
        if key in self.ufp:
            return self.ufp[key]
        else:
            return ""

    def __contains__(self, key):
        return key in self.ufp

    def tagwrap(self, tag, i):
        if i == 0:
            return tag in self.ufp["canto_state"]
        elif i == 1 and not tag in self.ufp["canto_state"]:
            self.ufp["canto_state"].append(tag)
        elif i == -1 and tag in self.ufp["canto_state"]:
            self.ufp["canto_state"].remove(tag)

        if self.feed:
            self.feed.has_changed()

    def wasread(self):
        return self.tagwrap("read", 0)

    def read(self):
        self.tagwrap("read", 1)

    def unread(self):
        self.tagwrap("read", -1)

    def marked(self):
        return self.tagwrap("marked", 0)

    def mark(self):
        self.tagwrap("marked", 1)

    def unmark(self):
        self.tagwrap("marked", -1)

    def isnew(self):
        return self.tagwrap("new", 0)

    def new(self):
        self.tagwrap("new", 1)

    def old(self):
        self.tagwrap("new", -1)

    def selected(self):
        return self.sel

    def select(self):
        self.sel = 1

    def unselect(self):
        self.sel = 0

    def print_item(self, cfg, tag, row, i):
        return self.renderer.story(cfg, tag, self, row, \
                i.cfg.gui_height, i.cfg.gui_width / i.cfg.columns, \
                i.window_list)

    def get_text(self):
        if "content" in self:
            for c in self["content"]:
                if "text" in c["type"]:
                    return c["value"]

        return self["description"]
