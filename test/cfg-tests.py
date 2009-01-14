#!/usr/bin/python
# -*- coding: utf-8 -*-

#Canto - ncurses RSS reader
#   Copyright (C) 2008 Jack Miller <jack@codezen.org>
#
#   This program is free software; you can redistribute it and/or modify
#   it under the terms of the GNU General Public License version 2 as 
#   published by the Free Software Foundation.

from unittest import TestCase, main
import canto.cfg

class TestCfg(TestCase):
    def setUp(self):
        self.c = canto.cfg.Cfg("/dev/null", "/dev/null", "/dev/null",
        "/dev/null")

class TestHookExceptions(TestCfg):
    def runTest(self):
        self.c.parse(\
"""
def bad_resize_hook(cfg):
    tmp = 1 / 0
resize_hook = bad_resize_hook
""")

        self.c.resize_hook(None)

class TestInstantiation(TestCfg):
    def runTest(self):
        self.c.parse(\
"""
from canto.extra import *
# Feed.renderer should be instantiated
add("someURL", renderer=renderer)

# So should default tag sorts and filters
default_tag_sorts([by_unread, [None, by_len()]])
default_tag_filters([None, show_unread(), show_marked])

# And global filters
filters=[ None, show_unread(), show_marked]

# And custom tags
add_tag("Sometag", sorts=[ by_unread, [None, by_len()]])
""")
        self.failUnless(hasattr(self.c.feeds[0].renderer, "__class__"))

        for s in [self.c.tag_sorts, self.c.cfgtags[0].sorts.list]:
            self.failUnless(hasattr(s[0], "__class__"))
            self.failUnless(hasattr(s[1][1], "__class__"))

        for l in [self.c.tag_filters, self.c.filters.list]:
            for i in l:
                self.failUnless((not i) or hasattr(i, "__class__"))

if __name__ == "__main__":
    main()
