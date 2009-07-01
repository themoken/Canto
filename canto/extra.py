# -*- coding: utf-8 -*-

#Canto - ncurses RSS reader
#   Copyright (C) 2008 Jack Miller <jack@codezen.org>
#
#   This program is free software; you can redistribute it and/or modify
#   it under the terms of the GNU General Public License version 2 as 
#   published by the Free Software Foundation.

from cfg.filters import Filter, all_filters
from cfg.sorts import Sort, all_sorts

import canto_html
import utility
import input

import subprocess
import locale
import time
import os
import re

def __add_hook_meta(list):
    def add_hook(r, func, **kwargs):
        l = getattr(r, list, None)
        def get_index(s):
            if type(kwargs[s] == str):
                f = getattr(r, kwargs[s], None)
            else:
                f = kwargs[s]
            if f in l:
                return l.index(f)
            else:
                print "Cannot insert %s %s %s, it isn't in the list!" %\
                        (func.func_name, s, f.func_name)
                return -2

        if "after" in kwargs:
            idx = get_index("after") + 1
        elif "before" in kwargs:
            idx = get_index("before")
        else:
            idx = len(l)

        if idx > -1:
            l.insert(idx, func)
    return add_hook

add_hook_pre_reader = __add_hook_meta("pre_reader")
add_hook_post_reader = __add_hook_meta("post_reader")
add_hook_pre_story = __add_hook_meta("pre_story")
add_hook_post_story = __add_hook_meta("post_story")

# Adds Slashdot department information to reader
#
# Usage :
#   r = get_default_renderer()
#   add_hook_pre_reader(r, add_slash_dept, before="reader_convert_html")
#

def add_slash_dept(dict):
	if "slash_department" in dict["story"]:
		dict["content"] = "%1from the " + dict["story"]["slash_department"]\
			+ " department%0<br /><br />" + dict["content"]

def add_info(r, item):
    realitem = item.lower()
    if realitem == "by":
        realitem = u"author"

    def hook(dict):
        if realitem in dict["story"]:
            dict["content"] = "%s : %s\n" %\
                    (item, dict["story"][realitem]) + dict["content"]

    add_hook_pre_reader(r, hook, after="reader_convert_html")

# Filter for filtering out all read stories.
#
# Usage : filters=[None, show_unread()]
#       then using [/] to cycle through.

class show_unread(Filter):
    def __str__(self):
        return "Show unread"

    def __call__(self, tag, item):
        return not item.was("read")

# Filter for filtering out all unread stories.
#
# Usage : filters=[None, show_marked()]
#       then using [/] to cycle through

class show_marked(Filter):
    def __str__(self):
        return "Show marked"

    def __call__(self, tag, item):
        return item.was("marked")

# A filter to take a keyword or regex and filter
# all stories that don't contain/match it.
#
# Usage : filters=[None, only_with("Obama")]
#         filters=[None, only_with(".*[Ll]inux.*", regex=True)]
#

class only_with(Filter):
    def __init__(self, keyword, **kwargs):
        self.precache = []
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

# Display feed when it has one or more of the specified tags
class with_tag_in(Filter):
    def __init__(self, *tags):
        self.tags = set(tags)
        self.precache = []

    def __str__(self):
        return "With Tags: %s" % '/'.join(self.tags)

    def __call__(self, tag, item):
        feed = [f for f in tag.cfg.feeds if f.path == item.ufp_path][0]
        tags=set(feed.tags)
        return bool(self.tags.intersection(tags))

# Display when all filters match
#
# Usage : filters=[all_of(with_tag_in('news'), show_unread)]

class all_of(Filter):
    def __init__(self, *filters):
        # XXX deferred validation
        self.filters = filters

        self.precache = []
        for f in filters:
            if not f:
                continue
            for pc in f.precache:
                if pc not in self.precache:
                    self.precache.append(pc)

    def __str__(self):
        return ' & '.join(["(%s)" % f for f in self.filters])

    def __call__(self, tag, item):
        return all([f(tag, item) for f in self.filters])

def register_filter(filt):
    if filt not in all_filters:
        all_filters.append(filt)

def register_sort(s):
    if s not in all_sorts:
        all_sorts.append(s)

def set_filter(filter):
    register_filter(filter)
    return lambda x : x.set_filter(filter)

def set_tag_filter(filter):
    register_filter(filter)
    return lambda x : x.set_tag_filter(filter)

def set_tag_sort(sort):
    register_sort(sort)
    return lambda x : x.set_tag_sort(sort)

def set_tags(tags):
    return lambda x : x.set_tagset(tags)

# Creates a keybind for searching for a keyword or regex.
#
# Usage : keys["1"] = search("Obama")
#         keys["2"] = search(".*[Ll]inux.*, regex=True)

def search(s, **kwargs):
    if "regex" in kwargs and kwargs["regex"]:
        return lambda x : x.do_inline_search(re.compile(s))
    else:
        return lambda x : x.do_inline_search(re.compile(".*" + s + ".*"))

# Creates a keybind to do a interactive search.
#
# Usage : keys["/"] = search_filter

def search_filter(gui):
    rex = input.input(gui.cfg, "Search Filter")
    if not rex:
        return gui.set_filter(None)
    elif rex.startswith("rgx:"):
        rex = rex[4:]
    else:
        rex = "(?i).*" + re.escape(rex) + ".*"

    return gui.set_filter(only_with(rex, regex=True))

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

# Creates a keybind to copy the URL of the current story to the clipboard.
# xclip must be available for this to work.
#
# Usage : keys["y"] = ["just_read", yank, "next_item"]

def yank(gui):
    xclip = subprocess.Popen('xclip -i', shell=True,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            stdin=subprocess.PIPE)
    try:
        xclip.stdin.write(gui.sel["link"])
        xclip.stdin.close()
        assert xclip.wait() == 0
    except (IOError, AssertionError):
        gui.cfg.log("xclip must be installed for yank to work!")
    else:
        gui.cfg.log("Yanked: %s" % gui.sel["title"])

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

class by_date(Sort):
    def __init__(self):
        self.precache = ["updated_parsed"]

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

class by_len(Sort):
    def __str__(self):
        return "By Length"

    def __call__(self, x, y):
        return len(x["title"]) - len(y["title"])

class by_content(Sort):
    def __str__(self):
        return "By Length of Content"

    def __call__(self, x, y):
        def get_text(story):
            s,links = canto_html.convert(story.get_text())
            return s

        return len(get_text(x)) - len(get_text(y))

class by_alpha(Sort):
    def __str__(self):
        return "Alphabetical"

    def __call__(self, x, y):
        for a, b in zip(x["title"],y["title"]):
            if ord(a) != ord(b):
                return ord(a) - ord(b)

        return len(x["title"]) - len(y["title"])

class by_unread(Sort):
    def __str__(self):
        return "By Unread"

    def __call__(self, x, y):
        if x.was("read") and not y.was("read"):
            return 1
        if y.was("read") and not x.was("read"):
            return -1
        return 0

class reverse_sort(Sort):
    def __init__(self, other_sort):
        # XXX deferred validation
        self.other_sort = other_sort
        self.precache = other_sort.precache

    def __str__(self):
        return "Reversed %s" % self.other_sort

    def __call__(self, x, y):
        return -1 * self.other_sort(x,y)
