# -*- coding: utf-8 -*-

#Canto - ncurses RSS reader
#   Copyright (C) 2007 Jack Miller <jack@codezen.org>
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
    def __init__(self, story, height, width, cfg):
        """Reader() encapsulates the pager type reader interface,
        with separate keys."""
        self.story = story
        self.cfg = cfg
        self.more = 0
        self.offset = 0
        self.height = 0
        self.width = 0
        self.show_links = 0
        self.max_height = height
        self.cfg.key_handlers.append(self)
        self.refresh(height, width)

    def refresh(self, height, width):
        """Refresh the window. With the reader, the line is written twice, to gauge the size
           and then two actually display it to the new sized window."""
        
        self.links = [(self.story["link"], "main link")]
        self.links.extend(utility.getlinks(self.story["descr"]))

        # Get the size.
        self.lines = self.cfg.render.reader(self.story, width, self.links, self.show_links, None)

        self.height, self.width = min(self.lines, height),width
        self.window = curses.newpad(self.lines, width)
        self.window.bkgdset(curses.color_pair(1))

        # Perform the write.
        self.cfg.render.reader(self.story, width, self.links, self.show_links, self.window)
        self.draw_elements()

    def draw_elements(self):
        """Actually perform the print operations to the curses screen."""
        self.more = self.lines - (self.height + self.offset)
        self.window.refresh(self.offset, 0, 0, 0, self.height - 1, self.width)

    def toggle_show_links(self):
        self.show_links = not self.show_links

        # If we're removing links, propagate a refresh to the window below us.
        if not self.show_links:
            self.cfg.key_handlers[-2].refresh(self.cfg.height, self.cfg.width)
        
        self.refresh(self.max_height, self.width)

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
        """Perform the actual goto."""
        try : i = int(s)
        except : return

        if i in range(len(self.links) + 1) :
            self.cfg.goto(self.links[i][0])
        self.draw_elements()

    def goto(self):
        """Get a link number."""
        input.Input(self.cfg, " Link Number ", self.__dogoto, self.height, self.width, self.cfg.log)
        return 1
    
    def key(self, t):
        """Simple function dispatcher. Unlike Gui(), any key that 
        is not interpreted, causes the reader to disappear."""

        if self.cfg.reader_key_list.has_key(t) and self.cfg.reader_key_list[t]:
            f = getattr(self, self.cfg.reader_key_list[t], None)
            if f and not f() :
                self.draw_elements()
        elif t != (curses.KEY_RESIZE, 0) and t != (-1, 0):
            self.destroy()
            return

    def destroy(self):
        self.cfg.pop_handler()
