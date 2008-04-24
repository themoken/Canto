# -*- coding: utf-8 -*-

#Canto - ncurses RSS reader
#   Copyright (C) 2007 Jack Miller <jack@codezen.org>
#
#   This program is free software; you can redistribute it and/or modify
#   it under the terms of the GNU General Public License version 2 as 
#   published by the Free Software Foundation.

import curses
import interface_draw

class Input :
    """Input() forms a more intelligent input box that is more
    flexible than a simple curses getstr(). For example, truncating
    the input at the edge of the screen."""

    def __init__(self, cfg, caption, func, height, width, log):
        self.height = 0
        self.width = 0
        self.caption = caption
        self.term = ""
        self.func = func
        self.log = log
        self.cfg = cfg
        self.cfg.key_handlers.append(self)
        self.refresh(height, width)

    def refresh(self, height, width):
        self.height, self.width = height, width
        self.window = curses.newpad(3, self.width)
        self.draw_elements()

    def draw_elements(self):
        tmp = self.term
        l = len(tmp)
        if l > self.width - 2 :
            tmp = tmp[(l - (self.width - 2)):]

        self.cfg.render.box(self.caption, self.width, self.window)
        self.window.move(1, 1)
        self.window.addstr(tmp)
        self.window.refresh(0,0,0,0,2,self.width)

    def key(self, t):
        if t == (27, 0):
            self.destroy()
            return
        elif t == (10, 0):
            self.destroy()
            self.callfunc()
            return
        elif t == (263, 0) and len(self.term) > 0 :
            self.term = self.term[:-1]
        elif t != (-1, 0) and t[0] < 256 and not t[1] : 
            self.term += chr(t[0])

        self.draw_elements()

    def callfunc(self):
        self.func(self.term)

    def destroy(self):
        self.cfg.pop_handler()
