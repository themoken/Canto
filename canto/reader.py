# -*- coding: utf-8 -*-

#Canto - ncurses RSS reader
#   Copyright (C) 2008 Jack Miller <jack@codezen.org>
#
#   This program is free software; you can redistribute it and/or modify
#   it under the terms of the GNU General Public License version 2 as 
#   published by the Free Software Foundation.

from basegui import BaseGui
from input import input
from const import *
import utility

import curses

class Reader(BaseGui):
    def __init__(self, cfg, tag, story, dead_call):

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
        self.tag = tag
        self.dead = dead_call

        self.refresh()

    def refresh(self):
        # It's unfortunate, but because the interface is so complex,
        # the only way to get the number of lines it will take to completely
        # render the reader, we actually have to render it to a None window
        # first.

        # A way to get this right off the bat would be nice, but I doubt
        # it would enhance the performance more than one iota.

        d = { "story" : self.story,
              "cfg" : self.cfg,
              "show_links" : self.show_links,
              "window" : None }

        if self.cfg.reader_orientation in ["top","bottom",None]:
            # First render for self.lines
            d["width"] = self.cfg.gui_width
            d["height"] = 0
            self.lines, self.links = self.tag.renderer.reader(d)

            # This is the default, old behavior (floating window)
            if not self.cfg.reader_orientation:
                d["width"] = self.cfg.gui_width
                d["height"] = min(self.lines, self.cfg.gui_height)
                self.top, self.right = (0,0)
            # Rendering the reader into a pre-existing space
            else:
                d["height"] = self.cfg.reader_lines
                d["width"] = self.cfg.gui_width
                if self.cfg.reader_orientation == "top":
                    self.top, self.right = (0,0)
                else:
                    self.top, self.right = (self.cfg.gui_height, 0)
        else:
            d["width"] = self.cfg.reader_lines
            d["height"] = 0

            self.lines, self.links = self.tag.renderer.reader(d)

            if self.cfg.reader_orientation == "left":
                self.top, self.right = (0, 0)
            else:
                self.top, self.right = (0, self.cfg.gui_width)
                
        self.window = curses.newpad(self.lines, d["width"])
        self.window.bkgdset(curses.color_pair(1))

        d["window"] = self.window
        self.width = d["width"]
        self.height = d["height"]

        self.lines, self.links = self.tag.renderer.reader(d)
        self.draw_elements()

    def draw_elements(self):
        self.more = self.lines - (self.height + self.offset)
        self.window.noutrefresh(self.offset, 0, self.top, self.right, \
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
        term = input(self.cfg, "Goto")
        if not term:
            return
        
        links = []
        terms = term.split(',')

        for t in terms:
            try:
                links.append(int(t))
            except:
                if t.count('-') == 1:
                    d = t.index('-')
                    a = t[:d]
                    b = t[(d+1):]
                    try:
                        a = int(a)
                        b = int(b)
                    except:
                        self.cfg.log("Unable to interpret range!")
                        return
                    for l in xrange(a,b + 1):
                        links.append(l)
                else:
                    self.cfg.log("Unable to interpret link!")
                    return

        out = "Going to link"
        if len(links) != 1:
            out += "s "
            for n in links[:-1]:
                out += "%d, " % n
            out += "and %d" % links[-1]
        else:
            out += " %d" % links[0]
        self.cfg.log(out)

        for l in links:
            self.dogoto(l)

    def dogoto(self, n):
        if n == None:
            return
        if n < len(self.links):
            utility.goto(self.links[n], self.cfg)
        return 1

    def destroy(self):
        self.window.erase()
        self.draw_elements()
        self.dead()
        return REDRAW_ALL
