# -*- coding: utf-8 -*-

#Canto - ncurses RSS reader
#   Copyright (C) 2008 Jack Miller <jack@codezen.org>
#
#   This program is free software; you can redistribute it and/or modify
#   it under the terms of the GNU General Public License version 2 as 
#   published by the Free Software Foundation.

import interface_draw
import curses

class Message :
    def __init__(self, cfg, message):
        self.cfg = cfg
        self.message = message
        self.refresh()

    def refresh(self):
        self.lines = self.cfg.default_renderer.message(\
                self.message, self.cfg.width, None)
        if self.lines == 3:
            width = len(self.message) + 4
        else:
            width = self.cfg.width
        self.window = curses.newpad(self.lines, self.cfg.width)
        self.window.bkgdset(curses.color_pair(1))
        self.cfg.default_renderer.message(self.message, width, self.window)
        self.window.refresh(0,0,0,self.cfg.width - width,\
                self.lines - 1,self.cfg.width - 1)
