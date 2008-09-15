# -*- coding: utf-8 -*-

#Canto - ncurses RSS reader
#   Copyright (C) 2008 Jack Miller <jack@codezen.org>
#
#   This program is free software; you can redistribute it and/or modify
#   it under the terms of the GNU General Public License version 2 as 
#   published by the Free Software Foundation.

import interface_draw

class slashdot_renderer(interface_draw.Renderer):
    def reader_head(self, story):
        title = self.do_regex(story["title"], [self.story_rgx, self.common_rgx])
        return [("%1%B" + title, " ", " "),\
                ("%bfrom the " + story["slash_department"] +\
                " department%B", " ", " "),("┌","─","┐%C")]

class show_unread():
    def __init__(self):
        self.name = "Show unread."

    def __call__(self, tag, item):
        return not item.wasread()
