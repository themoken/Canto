# -*- coding: utf-8 -*-

#Canto - ncurses RSS reader
#   Copyright (C) 2008 Jack Miller <jack@codezen.org>
#
#   This program is free software; you can redistribute it and/or modify
#   it under the terms of the GNU General Public License version 2 as 
#   published by the Free Software Foundation.

from input import input
from const import *
import utility

import curses

class Reader :
    def __init__(self, cfg, story, register, deregister):
        self.story = story
        self.cfg = cfg
        self.keys = cfg.reader_key_list

        self.more = 0
        self.offset = 0
        self.height = 0
        self.width = 0
        self.height = 0
        self.show_links = 0
        
        self.max_height = self.cfg.gui_height

        register(self)
        self.register = register
        self.deregister = deregister
        self.refresh()

    def refresh(self):
        self.lines, self.links = self.story.renderer.reader(self.story, \
                self.cfg.width, self.show_links, None)
        
        self.height, self.width = min(self.lines, self.max_height),\
                self.cfg.width
        self.window = curses.newpad(self.lines, self.cfg.width)
        self.window.bkgdset(curses.color_pair(1))

        self.story.renderer.reader(self.story, self.cfg.width, \
                self.show_links, self.window)
        self.draw_elements()

    def draw_elements(self):
        self.more = self.lines - (self.height + self.offset)
        self.window.refresh(self.offset, 0, 0, 0, self.height - 1, self.width)

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
        self.dogoto(input(self.cfg, "Link Number"))

    def dogoto(self, s):
        try : i = int(s)
        except:
            return

        if i < len(self.links):
            utility.goto(self.links[i], self.cfg)
        return 1

    def action(self, a):
        if callable(a):
            r = a()
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
        self.deregister()
