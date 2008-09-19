# -*- coding: utf-8 -*-

#Canto - ncurses RSS reader
#   Copyright (C) 2008 Jack Miller <jack@codezen.org>
#
#   This program is free software; you can redistribute it and/or modify
#   it under the terms of the GNU General Public License version 2 as 
#   published by the Free Software Foundation.

import interface_draw
import os
import re

class slashdot_renderer(interface_draw.Renderer):
    def reader_head(self, story):
        title = self.do_regex(story["title"], [self.story_rgx, self.common_rgx])
        return [("%1%B" + title, " ", " "),\
                ("%bfrom the " + story["slash_department"] +\
                " department%B", " ", " "),("┌","─","┐%C")]

class show_unread():
    def __str__(self):
        return "Show unread"

    def __call__(self, tag, item):
        return not item.wasread()

class show_marked():
    def __str__(self):
        return "Show marked"

    def __call__(self, tag, item):
        return item.marked()

class only_with():
    def __init__(self, keyword, **kwargs):
        self.keyword = keyword
        if kwargs.has_key("regex") and kwargs["regex"]:
            self.match = re.compile(keyword)
        else:
            self.match = re.compile(".*" + keyword + ".*")

    def __str__(self):
        return "With %s" % self.keyword

    def __call__(self, tag, item):
        return self.match.match(item["title"])

class only_without(only_with):
    def __call__(self, tag, item):
        return not self.match.match(item["title"])

def search(s, **kwargs):
    if kwargs.has_key("regex") and kwargs["regex"]:
        return lambda x : x.do_inline_search(re.compile(s))
    else:
        return lambda x : x.do_inline_search(re.compile(".*" + s + ".*"))

def set_xterm_title(tag, item):
    # Don't use print!
    os.write(1, "\033]0; %s - %s\007" % (tag.tag, item["title"]))

def clear_xterm_title(*args):
    os.write(1, "\033]0; \007")
