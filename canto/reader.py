# -*- coding: utf-8 -*-

#Canto - ncurses RSS reader
#   Copyright (C) 2008 Jack Miller <jack@codezen.org>
#
#   This program is free software; you can redistribute it and/or modify
#   it under the terms of the GNU General Public License version 2 as 
#   published by the Free Software Foundation.

from input import num_input
from const import *
import utility

import curses

class Reader :
    def __init__(self, cfg, story, register, deregister):
        self.story = story
        self.cfg = cfg
        self.keys = cfg.reader_key_list
        self.focus = 0
        self.more = 0
        self.offset = 0
        self.height = 0
        self.width = 0
        self.height = 0
        self.show_links = 0

        register(self)
        self.register = register
        self.deregister = deregister
        self.refresh()

    def __str__(self):
        if self.focus:
            return u"%B[" + self.story["title"][:10] + u"]%b"
        return u"[" + self.story["title"][:10] + u"]"

    def refresh(self):
        # It's unfortunate, but because the interface is so complex,
        # the only way to get the number of lines it will take to completely
        # render the reader, we actually have to render it to a None window
        # first.

        # A way to get this right off the bat would be nice, but I doubt
        # it would enhance the performance more than one iota.

        if self.cfg.reader_orientation in ["top","bottom",None]:
            # First render for self.lines
            self.lines, self.links = self.story.renderer.reader(self.cfg, \
                    self.story, self.cfg.width, self.show_links, None)

            # This is the default, old behavior (floating window)
            if not self.cfg.reader_orientation:
                self.height, self.width = min(self.lines, self.cfg.gui_height),\
                        self.cfg.width
                self.top, self.right = (0,0)
            # Rendering the reader into a pre-existing space
            else:
                self.height = self.cfg.reader_lines
                self.width = self.cfg.width
                if self.cfg.reader_orientation == "top":
                    self.top, self.right = (0,0)
                else:
                    self.top, self.right = (self.cfg.gui_height, 0)
        else:
            self.lines, self.links = self.story.renderer.reader(self.cfg, \
                    self.story, self.cfg.reader_lines, self.show_links, None)

            self.height = self.cfg.gui_height
            self.width = self.cfg.reader_lines

            if self.cfg.reader_orientation == "left":
                self.top, self.right = (0, 0)
            else:
                self.top, self.right = (0, self.cfg.gui_width)
                
        self.window = curses.newpad(self.lines, self.width)
        self.window.bkgdset(curses.color_pair(1))
        self.lines, self.links = self.story.renderer.reader(self.cfg, self.story, \
                self.width, self.show_links, self.window)

        self.draw_elements()

    def draw_elements(self):
        self.more = self.lines - (self.height + self.offset)
        self.window.refresh(self.offset, 0, self.top, self.right, \
                self.height - 1 + self.top, self.width + self.right)

    def toggle_show_links(self):
        self.show_links = not self.show_links
        self.refresh()

        if not self.show_links:
            return REDRAW_ALL

    def scroll_down(self):
        if self.more > 0 :
            self.offset += 1

    def page_down(self):
        if self.more > self.height:
            self.offset += self.height
        else:
            self.offset = self.lines - self.height

    def scroll_up(self):
        if self.offset :
            self.offset -= 1
    
    def page_up(self):
        if self.offset > self.height:
            self.offset -= self.height
        else:
            self.offset = 0

    def goto(self):
        self.dogoto(num_input(self.cfg, u"Link Number"))

    def dogoto(self, n):
        if n == None:
            return
        if n < len(self.links):
            utility.goto(self.links[n], self.cfg)
        return 1

    def switch(self):
        return WINDOW_SWITCH

    def alarm(self, a=None, b=None):
        pass
    
    def action(self, a):
        if hasattr(a, "__call__"):
            r = a(self)
        else:
            r = 0
            f = getattr(self,a,None)
            if f:
                r = f()

        if not r:
            self.draw_elements()
        return r

    def quit(self):
        self.destroy()
        return REDRAW_ALL

    def destroy(self):
        self.window.erase()
        self.draw_elements()
        self.deregister()
