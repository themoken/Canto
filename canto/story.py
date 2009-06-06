# -*- coding: utf-8 -*-

#Canto - ncurses RSS reader
#   Copyright (C) 2008 Jack Miller <jack@codezen.org>
#
#   This program is free software; you can redistribute it and/or modify
#   it under the terms of the GNU General Public License version 2 as 
#   published by the Free Software Foundation.

class Story():
    def __init__(self, d, get_ufp):
        self.updated = 0
        self.get_ufp = get_ufp
        self.d = d
        self.sel = 0
    
    def __eq__(self, other):
        if self["id"] != other["id"]:
            return 0

        # The reason that we have to check for membership is
        # that sometimes (like when writing to disk) it's convenient
        # to compare against a dict in the feedparser block than
        # another Story object. In all of these cases, the feeds
        # are guaranteed to be the same anyway.

        if "feed" in other and (self["feed"] != other["feed"]):
            return 0

        return 1

    def __str__(self):
        return self.d["title"] + " " + str(id(self))

    def get_ufp_entry(self):
        ufp = self.get_ufp()
        if not ufp:
            return None
        for ondisk in ufp["entries"]:
            if ondisk["id"] == self["id"]:
                break
        else:
            return None
        return ondisk

    def __getitem__(self, key):
        if key in self.d:
            return self.d[key]
        else:
            ondisk = self.get_ufp_entry()
            if not ondisk:
                return ""
            if key in ondisk:
                return ondisk[key]
            return ""

    def __setitem__(self, key, item):
        self.d[key] = item

    def __contains__(self, key):
        if key in self.d:
            return True
        else:
            ondisk = self.get_ufp_entry()
            return key in ondisk

    def was(self, tag):
        return tag in self.d["canto_state"]

    def set(self, tag):
        if not tag in self.d["canto_state"]:
            self.d["canto_state"].append(tag)
            self.updated = 1
    
    def unset(self,tag):
        if tag in self.d["canto_state"]:
            self.d["canto_state"].remove(tag)
            self.updated = 1

    def selected(self):
        return self.sel

    def select(self):
        self.sel = 1

    def unselect(self):
        self.sel = 0

    def get_text(self):
        if "content" in self:
            for c in self["content"]:
                if "text" in c["type"]:
                    return c["value"]

        return self["description"]
