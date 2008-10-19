# -*- coding: utf-8 -*-

#Canto - ncurses RSS reader
#   Copyright (C) 2008 Jack Miller <jack@codezen.org>
#
#   This program is free software; you can redistribute it and/or modify
#   it under the terms of the GNU General Public License version 2 as 
#   published by the Free Software Foundation.

import curses
import interface_draw

class Input :
    def __init__(self, cfg, caption, func, register, deregister):
        self.caption = caption
        self.term = ""
        
        self.func = func
        self.cfg = cfg

        register(self)
        self.register = register
        self.deregister = deregister
        self.refresh()

    def refresh(self):
        self.window = curses.newpad(3, self.cfg.width)
        self.window.bkgdset(curses.color_pair(1))
        self.draw_elements()

    def draw_elements(self):
        tmp = self.term
        l = len(tmp)
        if l > self.cfg.width - 2 :
            tmp = tmp[(l - (self.cfg.width - 2)):]

        self.cfg.default_renderer.box(self.caption, self.cfg.width, self.window)
        self.window.move(1, 1)
        self.window.addstr(tmp)
        self.window.refresh(0,0,0,0,2,self.cfg.width)

    def action(self, t):
        if t == (27, 0):
            self.destroy()
            return
        elif t == (10, 0):
            self.destroy()
            self.callfunc()
            return
        elif t == (curses.KEY_BACKSPACE, 0) and len(self.term) > 0 :
            self.term = self.term[:-1]
        elif t != (-1, 0) and t[0] < 256 and not t[1] : 
            self.term += chr(t[0])

        self.draw_elements()

    def callfunc(self):
        self.func(self.term)
    
    def alarm(self, stories):
        pass

    def destroy(self):
        self.deregister()
