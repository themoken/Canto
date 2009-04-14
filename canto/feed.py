# -*- coding: utf-8 -*-

#Canto - ncurses RSS reader
#   Copyright (C) 2008 Jack Miller <jack@codezen.org>
#
#   This program is free software; you can redistribute it and/or modify
#   it under the terms of the GNU General Public License version 2 as 
#   published by the Free Software Foundation.

from const import VERSION_TUPLE
import story
import tag

import cPickle
import fcntl

# Feed() controls a single feed and implements all of the update functionality
# on top of Tag() (which is the generic class for lists of items). Feed() is
# also the lowest granule for custom renderers because the renderers are
# most likely using information specific to the XML, rather than information
# specific to an arbitrary list.

# Each feed has a self.ufp item that contains a verbatim copy of the data
# returned by the feedparser.

# Each feed will also only write its status back to disk on tick() and only if
# has_changed() has been called by one of the Story() items Feed() contains.

class Feed(list):
    def __init__(self, cfg, dirpath, URL, tags, rate, keep, \
            renderer, filter, username, password):

        # Configuration set settings
        self.tags = tags
        self.base_set = 0

        self.URL = URL
        self.renderer = renderer
        self.rate = rate
        self.time = 1
        self.keep = keep
        self.username = username
        self.password = password

        # Hard filter
        if filter:
            self.filter = lambda x: filter(self, x)
        else:
            self.filter = None

        # Other necessities
        self.path = dirpath
        self.cfg = cfg
        self.changed = 0
        self.ufp = None
   
    def update(self):
        lockflags = fcntl.LOCK_SH
        if self.base_set:
            lockflags |= fcntl.LOCK_NB

        try:
            f = open(self.path, "r")
            try:
                fcntl.flock(f.fileno(), lockflags)
                self.ufp = cPickle.load(f)
            except:
                return 0
            finally:
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)
                f.close()
        except:
            return 0

        # If this data pre-dates 0.6.0 (the last disk format update)
        # toss a key error.
        if "canto_version" not in self.ufp or\
                self.ufp["canto_version"][1] < 6:
            raise KeyError

        if not self.base_set:
            self.base_set = 1
            if "feed" in self.ufp and "title" in self.ufp["feed"]:
                replace = lambda x: x or self.ufp["feed"]["title"]
                self.tags = [ replace(x) for x in self.tags]
            else:
                # Using URL for tag, no guarantees
                self.tags = [self.URL] + self.tags

        self.extend(self.ufp["entries"])
        return 1

    def extend(self, entries):
        newlist = []
        for entry in entries:
            # If out todisk() lock failed, then it's possible
            # we have unwritten changes, so we need to move over
            # the canto_state, rather than just using the already
            # written one.

            selected = 0

            if entry in self:
                i = self.index(entry)
                if self.changed and entry["canto_state"] !=\
                        self[i]["canto_state"]:
                    entry["canto_state"] = self[i]["canto_state"]
                    self.has_changed()
                selected = self[i].sel

            # If tags were added in the configuration, c-f won't
            # notice (doesn't care about tags), so we check and
            # append as needed.

            for tag in self.tags:
                if tag not in entry["canto_state"]:
                    entry["canto_state"].append(tag)

            s = story.Story(entry, self, self.renderer)
            s.sel = selected
            newlist.append(s)

        del self[:]
        list.extend(self, filter(self.filter, newlist))

    def has_changed(self):
        self.changed = 1

    def todisk(self):
        f = open(self.path, "r+")
        try:
            fcntl.flock(f.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            f.seek(0, 0)
            f.truncate()
            cPickle.dump(self.ufp, f)
            f.flush()
        except:
            return 0
        finally:
            fcntl.flock(f.fileno(), fcntl.LOCK_UN)
            f.close()

        self.changed = 0
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
