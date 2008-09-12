# -*- coding: utf-8 -*-

#Canto - ncurses RSS reader
#   Copyright (C) 2008 Jack Miller <jack@codezen.org>
#
#   This program is free software; you can redistribute it and/or modify
#   it under the terms of the GNU General Public License version 2 as 
#   published by the Free Software Foundation.

from const import *
import os
import cfg
import curses
import utility
import re
import search
import feed
import reader
import sys
import tag
import message

# Gui() is the class encompassing the basic view of canto,
# the list of feeds (tags) and items.

# Gui()'s main data structure is self.list, which is a list
# of arbitrary Tag() objects, each being a list of stories.
# A corresponding list is self.map, which maps out the visible
# stories in order of appearance.

# Self.map may seem redundant, but it's mostly for convenience.
# For example, if the items are globally sorted, then iterating
# over self.list won't work. Or if you're testing membership
# of a story in the self. list (see __select_topoftag).
# Or if your iterating over all visible items (see draw_elements)

# Self.list is still useful though, when dealing with things
# like tag based sorting, or setting the attributes of a Tag()
# since each story doesn't have access to its Tag() object
# directly.

class Gui :
    def __init__(self, cfg, list, tags, register, deregister):
        self.cfg = cfg
        self.safe_attrs = ["help","quit","next_filter","prev_filter"] 
        self.lines = 0
        self.window_list = []
        self.sel = 0
        self.items = 0

        self.offset = 0
        self.max_offset = 0

        self.message = None

        register(self)
        self.register = register
        self.deregister = deregister

        self.map = []
        self.list = tags
        for t in self.list:
            t.extend(list)

        for t in self.list :
            if len(t):
                self.sel = t[0]
                self.sel_idx = 0
                t[0].select()
                break
        else:
            self.message = message.Message(self.cfg, "No Items.")
            return

        self.refresh()

    def refresh(self):
        self.window_list = [curses.newwin(self.cfg.height + 1, \
                    self.cfg.width / self.cfg.columns, 0, \
                    (self.cfg.width / self.cfg.columns) * i) \
                    for i in range(0, self.cfg.columns)]

        for window in self.window_list:
            window.bkgdset(curses.color_pair(1))
        self.lines = self.cfg.columns * self.cfg.height
        self.__map_items()
        self.draw_elements()

    def __map_items(self):
        row = 0
        self.map = []
        for i, feed in enumerate(self.list):
            for item in feed:
                if not feed.collapsed or item.idx == 0:
                    item.lines = item.print_item(feed, 0, self)
                    if item.lines:
                        item.feed_idx = i
                        item.row = row
                        row += item.lines
                        self.map.append(item)
        
        self.items = len(self.map)
        if self.items:
            self.max_offset = self.map[-1].row + self.map[-1].lines - self.lines

    def draw_elements(self):
        if self.items > 0:
            self.__check_scroll()
            row = -1 * self.offset
            for item in self.map:
                if item.row + item.lines > self.offset:
                    if item.row > self.lines + self.offset:
                        break
                    item.print_item(self.list[item.feed_idx], row, self)
                row += item.lines
        else:
            row = -1
        
        for i in range(len(self.window_list)) :
            if i * self.cfg.height > row:
                self.window_list[i].clear()
            else:
                self.window_list[i].clrtobot()
            self.window_list[i].noutrefresh()
        curses.doupdate()
        if self.message:
            self.message.refresh()

    def __check_scroll(self) :
        if self.sel.row < self.offset :
            self.offset = self.sel.row
            return 1

        if self.sel.row + self.sel.lines > self.lines + self.offset :
            self.offset = self.sel.row + self.sel.lines - self.lines
            return 1
        return 0

    def alarm(self, listobj):
        for t in self.list:
            t.clear()
            t.extend(listobj)
        self.__map_items() 

        if self.items > 0:
            if self.message:
                self.message = None
            if self.sel:
                r = self.list[self.sel.feed_idx].search_stories(self.sel)
                if r != -1  :
                    self.sel = self.list[self.sel.feed_idx][r]
                    self.sel.select()
                else:
                    self.__select_topoftag(self.sel.feed_idx)
            else:
                self.__select_topoftag(0)
        elif self.sel and not self.message:
            self.message = message.Message(self.cfg, "No Items.")
            self.sel = None
        self.draw_elements()
    
    def key(self, t):
        if self.cfg.key_list.has_key(t) and self.cfg.key_list[t] :
            if self.items:
                if self.message:
                    self.message = None
            elif self.cfg.key_list[t] not in self.safe_attrs:
                if not self.message:
                    self.message = message.Message(self.cfg, "No Items.")
                return

            f = getattr(self, self.cfg.key_list[t], None)
            if f:
                r = f()
                if not r:
                    self.draw_elements()
                return r

    def change_selected(fn):
        def dec(self, *args):
            self.sel.unselect()
            r = fn(self, *args)
            self.sel = self.map[self.sel_idx]
            self.sel.select()
            return r
        return dec

    @change_selected
    def __select_topoftag(self, f=0):
        for feed in self.list[f:]:
            for item in feed:
                if item in self.map:
                    self.sel = item
                    return

    @change_selected
    def next_item(self):
        if self.sel_idx < self.items :
            self.sel_idx += 1

    @change_selected
    def prev_item(self):
        if self.sel_idx > 0 :
            self.sel_idx -= 1

    def prev_tag(self) :
        curtag = self.sel.feed_idx
        while not self.sel_idx == 0 :
            if curtag != self.sel.feed_idx and self.sel.idx == 0:
                break
            self.prev_item()

    def next_tag(self) :
        curtag = self.sel.feed_idx
        while not self.sel_idx == self.items :
            if curtag != self.sel.feed_idx:
                break
            self.next_item()
        self.offset = min(self.sel.row, max(0, self.max_offset))

    @change_selected
    def __next_attr(self, attr, status) :
        cursor = self.sel
        while cursor.next:
            if getattr(cursor.next, attr)() == status:
                self.sel = cursor.next
                break
            cursor = cursor.next

    @change_selected
    def __prev_attr(self, attr, status) :
        cursor = self.sel
        while cursor.prev:
            if getattr(cursor.prev, attr)() == status:
                self.sel = cursor.prev
                break
            cursor = cursor.prev

    def next_mark(self):
        self.__next_attr("marked", 1)

    def prev_mark(self):
        self.__prev_attr("marked", 1)

    def next_unread(self):
        self.__next_attr("wasread", 0)

    def prev_unread(self):
        self.__prev_attr("wasread", 0)

    def just_read(self):
        self.list[self.sel.feed_idx].set_read(self.sel.idx)

    def just_unread(self):
        self.list[self.sel.feed_idx].set_unread(self.sel.idx)

    def goto(self) :        
        self.list[self.sel.feed_idx].set_read(self.sel.idx)
        self.draw_elements()
        utility.goto(self.sel["link"], self.cfg)

    def help(self):
        utility.silentfork("man canto", 1)
        return REDRAW_ALL

    def reader(self) :
        self.list[self.sel.feed_idx].set_read(self.sel.idx)
        reader.Reader(self.cfg, self.sel, self.register, self.deregister) 
        return REDRAW_ALL

    def next_filter(self):
        if self.cfg.next_filter():
            return ALARM

    def prev_filter(self):
        if self.cfg.prev_filter():
            return ALARM

    def inline_search(self):
        search.Search(self.cfg, " Inline Search ", \
                self.__do_inline_search, self.register, self.deregister)
        return REDRAW_ALL

    def __do_inline_search(self, s) :
        if s:
            for t in self.list:
                for story in t:
                    if s.match(story["title"]):
                        story.mark()
                    else:
                        story.unmark()

        self.prev_mark()
        self.next_mark()
        self.draw_elements()

    def toggle_mark(self):
        if self.sel.marked() :
            self.sel.unmark()
        else:
            self.sel.mark()

    def toggle_collapse_tag(self):
        self.list[self.sel.feed_idx].collapsed =\
                not self.list[self.sel.feed_idx].collapsed
        self.sel.unselect()
        self.__map_items()
        self.__select_topoftag(self.sel.feed_idx)

    def __collapse_all(self, c):
        for t in self.list:
            t.collapsed = c
        self.__map_items()
        self.__select_topoftag(self.sel.feed_idx)

    def set_collapse_all(self):
        self.__collapse_all(1)

    def unset_collapse_all(self):
        self.__collapse_all(0)

    def force_update(self):
        for f in self.cfg.feeds :
            f.time = 1
        return ALARM

    def tag_read(self):
        self.list[self.sel.feed_idx].all_read()

    def all_read(self):
        for t in self.list:
            t.all_read()

    def tag_unread(self):
        self.list[self.sel.feed_idx].all_unread()

    def all_unread(self):
        for t in self.list :
            t.all_unread()

    def quit(self):
        self.deregister()
        return -1
