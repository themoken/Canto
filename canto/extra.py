# -*- coding: utf-8 -*-

#Canto - ncurses RSS reader
#   Copyright (C) 2008 Jack Miller <jack@codezen.org>
#
#   This program is free software; you can redistribute it and/or modify
#   it under the terms of the GNU General Public License version 2 as 
#   published by the Free Software Foundation.

import interface_draw
import utility

import locale
import time
import os
import re

# Adds Slashdot department information to reader
#
# Usage : addfeed("Slashdot",\
#        "http://rss.slashdot.org/slashdot/Slashdot", \
#        renderer=slashdot_renderer()

class slashdot_renderer(interface_draw.Renderer):
    def reader_head(self, dict):
        title = self.do_regex(dict["story"]["title"], self.story_rgx)
        return [(u"%1%B" + title, u" ", u" "),\
                (u"%bfrom the " + dict["story"]["slash_department"] +\
                u" department%B", u" ", u" "),(u"┌",u"─",u"┐%C")]

# Adds a "tablist" to the default Canto config.

def tabbed_status(cfg):
    return u"%8%BCanto » %b%2" + \
            " ".join([unicode(x) for x in cfg.key_handlers]) + u"%1"

# Filter for filtering out all read stories.
#
# Usage : filterlist=[None, show_unread()]
#       then using [/] to cycle through.

class show_unread():
    def __str__(self):
        return "Show unread"

    def __call__(self, tag, item):
        return not item.wasread()

# Filter for filtering out all unread stories.
#
# Usage : filterlist=[None, show_marked()]
#       then using [/] to cycle through

class show_marked():
    def __str__(self):
        return "Show marked"

    def __call__(self, tag, item):
        return item.marked()

# A filter to take a keyword or regex and filter
# all stories that don't contain/match it.
#
# Usage : filterlist=[None, only_with("Obama")]
#         filterlist=[None, only_with(".*[Ll]inux.*", regex=True)]
#

class only_with():
    def __init__(self, keyword, **kwargs):
        self.keyword = keyword
        if "regex" in kwargs and kwargs["regex"]:
            self.match = re.compile(keyword)
        else:
            self.match = re.compile(".*" + keyword + ".*")

    def __str__(self):
        return "With %s" % self.keyword

    def __call__(self, tag, item):
        return self.match.match(item["title"])

# Same as above, except filters out all stories that
# *do* match the keyword / regex.

class only_without(only_with):
    def __str__(self):
        return "Without %s" % self.keyword

    def __call__(self, tag, item):
        return not self.match.match(item["title"])

def set_filter(filter):
    return lambda x : x.set_filter(filter)

def set_tag_filter(filter):
    return lambda x : x.set_tag_filter(filter)

def set_tag_sort(sort):
    sort = utility.get_list_of_instances(sort)
    return lambda x : x.set_tag_sort(sort)

# Creates a keybind for searching for a keyword or regex.
#
# Usage : keys["1"] = search("Obama")
#         keys["2"] = search(".*[Ll]inux.*, regex=True)

def search(s, **kwargs):
    if "regex" in kwargs and kwargs["regex"]:
        return lambda x : x.do_inline_search(re.compile(s))
    else:
        return lambda x : x.do_inline_search(re.compile(".*" + s + ".*"))

# Creates a keybind to append current story information to a file in the user's
# home directory. This is merely an example, but with a little modification it
# could be used to output XML chunks or Markdown output, etc.
# 
# Usage : keys["s"] = save

def save(x):
    file = open(os.getenv("HOME")+"/canto_out", "a")
    file.write(x.sel["title"] + "\n")
    file.write(x.sel["link"] + "\n\n")
    file.close()

# Note: the following two hacks are for xterm and compatible
# terminal emulators ([u]rxvt, eterm, aterm, etc.). These should
# not be run in screen or standard linux terms because they'll
# print garbage to the screen.

# Sets the xterm_title to Feed - Title
#
# Usage : select_hook = set_xterm_title

def set_xterm_title(tag, item):
    # Don't use print!
    prefcode = locale.getpreferredencoding()
    os.write(1, (u"\033]0; %s - %s\007" % \
            (tag.tag, item["title"])).encode(prefcode))

# Sets the xterm title to " "
#
# Usage : end_hook = clear_xterm_title

def clear_xterm_title(*args):
    os.write(1, "\033]0; \007")

# SORTS

class by_date:
    def __str__(self):
        return "By Date"

    def __call__(self, x, y):
        # We wrap this, despite the fact that sorts are all
        # wrapped in an exception logger because this is a
        # normal, unimportant problem.

        try:
            a = int(time.mktime(x["updated_parsed"]))
            b = int(time.mktime(y["updated_parsed"]))
        except:
            return 0

        return b - a

class by_len:
    def __str__(self):
        return "By Length"

    def __call___(self, x, y):
        return len(x["title"]) - len(y["title"])

class by_alpha:
    def __str__(self):
        return "Alphabetical"

    def __call__(self, x, y):
        for a, b in zip(x["title"],y["title"]):
            if ord(a) != ord(b):
                return ord(a) - ord(b)

        return len(x["title"]) - len(y["title"])

class by_unread:
    def __str__(self):
        return "By Unread"

    def __call__(self, x, y):
        if x.wasread() and not y.wasread():
            return 1
        if y.wasread() and not x.wasread():
            return -1
        return 0

class reverse_sort:
    def __init__(self, other_sort):
        self.other_sort = utility.get_instance(other_sort)

    def __str__(self):
        return "Reversed %s" % self.other_sort

    def __call__(self, x, y):
        return -1 * self.other_sort(x,y)
