# -*- coding: utf-8 -*-

#Canto - ncurses RSS reader
#   Copyright (C) 2008 Jack Miller <jack@codezen.org>
#
#   This program is free software; you can redistribute it and/or modify
#   it under the terms of the GNU General Public License version 2 as 
#   published by the Free Software Foundation.

# Story is a slick little class. It's main purpose is to hold all of the data
# for each story, both content and state. To save memory, 0.7.0 will attempt to
# fetch data from disk if it's not held by default. A good example is
# description information which can take up kilobytes or megabytes of memory but
# are rarely used.

# Story doesn't care which feed or tag it's associated with. If you really want
# to get the feed, story["feed"] contains the unique URL, but you'd have to use
# the config to get the Feed() object. The only thing that the Story() gets from
# the feed is the get_ufp function that gets the feedparser dict from disk.

from const import STORY_SAVED, STORY_UPDATED
import cPickle
import fcntl

class Story():
    def __init__(self, d, ufp_path, updated):
        self.updated = updated
        self.ufp_path = ufp_path
        self.ondisk = None
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

    # Where get_ufp reads the ufp from disk, this narrows that down to a
    # particular feed entry.

    def get_ufp_entry(self):
        try:
            f = open(self.ufp_path, "r")
            try:
                fcntl.flock(f.fileno(), fcntl.LOCK_SH)
                ufp = cPickle.load(f)
            except:
                return {}
            finally:
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)
                f.close()
        except:
            return {}

        for ondisk in ufp["entries"]:
            if ondisk["id"] == self["id"]:
                break
        else:
            self.ondisk = None
        self.ondisk = ondisk

    def __getitem__(self, key):
        if key in self.d:
            return self.d[key]

        # If the key isn't stored by default, get it from disk.
        else:
            if not self.ondisk:
                self.get_ufp_entry()
            if not self.ondisk:
                return ""
            if key in self.ondisk:
                return self.ondisk[key]
            return ""

    def __setitem__(self, key, item):
        self.d[key] = item

    def __contains__(self, key):
        if key in self.d:
            return True
        else:
            if not self.ondisk:
                self.get_ufp_entry()
            if not self.ondisk:
                return False
            return key in self.ondisk

    def was(self, tag):
        return tag in self.d["canto_state"]

    def set(self, tag):
        if not tag in self.d["canto_state"]:
            self.d["canto_state"].append(tag)
            self.updated = STORY_UPDATED
    
    def unset(self,tag):
        if tag in self.d["canto_state"]:
            self.d["canto_state"].remove(tag)
            self.updated = STORY_UPDATED

    # These are separate from the was/set/unset since the selected status isn't
    # stored in the ufp.

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

    # Free makes the Story() forget all of the uncommon items. Should be called
    # after anything that could cause Story() to fetch items (ie. in the
    # Renderer hooks).

    def free(self):
        if self.ondisk:
            self.ondisk = None
