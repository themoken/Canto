# -*- coding: utf-8 -*-

#Canto - ncurses RSS reader
#   Copyright (C) 2008 Jack Miller <jack@codezen.org>
#
#   This program is free software; you can redistribute it and/or modify
#   it under the terms of the GNU General Public License version 2 as 
#   published by the Free Software Foundation.

import interface_draw
import utility
import curses
import re
import input 

class Reader :
    def __init__(self, cfg, story, register, deregister):
        self.story = story
        self.cfg = cfg
        
        self.more = 0
        self.offset = 0
        self.height = 0
        self.width = 0
        self.height = 0
        self.show_links = 0
        
        self.max_height = self.cfg.height

        register(self)
        self.register = register
        self.deregister = deregister
        self.refresh()

    def refresh(self):
        self.links = [(self.story["link"], "main link")]
        self.links.extend(utility.getlinks(self.story["description"]))

        self.lines = self.cfg.render.reader(self.story, self.cfg.width, self.links, self.show_links, None)

        self.height, self.width = min(self.lines, self.cfg.height), self.cfg.width
        self.window = curses.newpad(self.lines, self.cfg.width)
        self.window.bkgdset(curses.color_pair(1))

        self.cfg.render.reader(self.story, self.cfg.width, self.links, self.show_links, self.window)
        self.draw_elements()

    def draw_elements(self):
        self.more = self.lines - (self.height + self.offset)
        self.window.refresh(self.offset, 0, 0, 0, self.height - 1, self.width)

    def toggle_show_links(self):
        self.show_links = not self.show_links

        if not self.show_links:
            return 1
        else: 
            self.refresh()

    def reader_next(self):
        self.destroy()
        return 2
 
    def reader_prev(self):
        self.destroy()
        return 3

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

    def __dogoto(self, s):
        try : i = int(s)
        except:
            return

        if i in range(len(self.links)) :
            utility.goto(self.links[i][0], self.cfg)
        self.draw_elements()

    def goto(self):
        input.Input(self.cfg, " Link Number ", self.__dogoto, self.register, self.deregister)
        return 1
    
    def key(self, t):
        if self.cfg.reader_key_list.has_key(t) and self.cfg.reader_key_list[t]:
            f = getattr(self, self.cfg.reader_key_list[t], None)
            if f:
                r = f()
                if not r:
                    self.draw_elements()
                return r

        elif t != (curses.KEY_RESIZE, 0):
            self.destroy()
            return

    def destroy(self):
        self.deregister()
