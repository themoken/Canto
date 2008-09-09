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

# Gui()'s main data structure is the map[] list. Similar
# to the 

class Gui :
    def __init__(self, cfg, list, tags, register, deregister):
        self.cfg = cfg
        
        self.lines = 0
        self.window_list = []
        self.map = list
        self.selected = 0
        self.items = 0

        self.offset = 0
        self.max_offset = 0

        self.message = None

        register(self)
        self.register = register
        self.deregister = deregister

        self.list = tags
        for t in self.list:
            t.extend(list)

        for t in self.list :
            if len(t):
                self.selected = t[0]
                t[0].select()
                break
        else:
            self.message = message.Message(self.cfg, "No Items.")
            return

        self.refresh()

    def refresh(self):
        self.window_list = [curses.newwin(self.cfg.height + 1, \
                    self.cfg.width / self.cfg.columns, 0, \
                    (self.cfg.width / self.cfg.columns) * i) for i in range(0, self.cfg.columns)]

        for window in self.window_list:
            window.bkgdset(curses.color_pair(1))
        self.lines = self.cfg.columns * self.cfg.height
        self.__map_items()
        self.draw_elements()

    def __map_items(self):
        row = 0
        prev = None
        prev_feed_item = None

        self.items = 0

        for i, feed in enumerate(self.list):
            for item in feed:
                if feed.collapsed and item.idx != 0:
                    item.visible = 0
                else:
                    item.lines = item.print_item(feed, 0, self)
                    if not item.lines:
                        item.visible = 0
                    else:
                        item.visible = 1
                        item.feed_idx = i
                        item.row = row
                        
                        if prev:
                            if i != prev.feed_idx:
                                item.prev_feed = prev_feed_item
                                prev.next_feed = item
                                prev_feed_item = item
                            else:
                                item.prev_feed = None
                                prev.next_feed = None

                            prev.next = item

                        item.prev = prev
                        prev = item
                        self.items += 1
                        row += item.lines

        if prev:
            self.max_offset = prev.row + prev.lines - self.lines

    def key(self, t):
        if self.cfg.key_list.has_key(t) and self.cfg.key_list[t] :
            if not self.items and self.cfg.key_list[t] not in ["help", "quit", "next_filter","prev_filter"]:
                if not self.message:
                    self.message = message.Message(self.cfg, "No Items.")
                return

            f = getattr(self, self.cfg.key_list[t], None)
            if f:
                r = f()
                if not r:
                    self.draw_elements()
                return r

    def help(self):
        utility.silentfork("man canto", 1)
        return REDRAW_ALL

    def alarm(self, listobj):
        for t in self.list:
            t.clear()
            t.extend(listobj)
        self.__map_items() 

        if self.items > 0:
            if self.selected:
                r = self.list[self.selected.feed_idx].search_stories(self.selected)
                if r != -1  :
                    self.selected = self.list[self.selected.feed_idx][r]
                    self.selected.select()
                else:
                    self.__select_topoftag(self.selected.feed_idx)
            else:
                self.__select_topoftag(0)
        elif self.selected and not self.message:
            self.message = message.Message(self.cfg, "No Items.")
            self.selected = None
        self.draw_elements()
    
    def change_selected(fn):
        def dec(self, *args):
            if self.selected:
                self.selected.unselect()
            fn(self, *args)
            if self.selected:
                self.selected.select()
        return dec

    @change_selected
    def __select_topoftag(self, f=0):
        for feed in self.list[f:]:
            for item in feed:
                if item.visible:
                    self.selected = item
                    return

    def __check_scroll(self) :
        if self.selected.row < self.offset :
            self.offset = self.selected.row
            return 1

        if self.selected.row + self.selected.lines > self.lines + self.offset :
            self.offset = self.selected.row + self.selected.lines - self.lines
            return 1
        return 0

    def draw_elements(self):
        if self.items > 0:
            self.__check_scroll()
            row = -1 * self.offset
            for feed in self.list:
                for item in feed:
                    if item.row + item.lines > self.offset:
                        if item.row > self.lines + self.offset:
                            break
                        item.print_item(feed, row, self)
                    row += item.lines
                else:
                    continue
                break
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

    @change_selected
    def next_item(self):
        if self.selected.next :
            self.selected = self.selected.next
    
    @change_selected
    def prev_item(self):
        if self.selected.prev :
            self.selected = self.selected.prev

    @change_selected
    def prev_tag(self) :
        while self.selected.prev and not self.selected.prev_feed:
            self.selected = self.selected.prev
        if self.selected.prev_feed:
            self.selected = self.selected.prev_feed
    
    @change_selected
    def next_tag(self) :
        while self.selected.next and not self.selected.next_feed:
            self.selected = self.selected.next
        if self.selected.next_feed:
            self.selected = self.selected.next_feed
        self.offset = -1 * min(self.selected.row,self.max_offset)

    def just_read(self):
        self.list[self.selected.feed_idx].set_read(self.selected.idx)

    def just_unread(self):
        self.list[self.selected.feed_idx].set_unread(self.selected.idx)

    def goto(self) :        
        self.list[self.selected.feed_idx].set_read(self.selected.idx)
        self.draw_elements()
        utility.goto(self.selected["link"], self.cfg)

    def reader(self) :
        self.list[self.selected.feed_idx].set_read(self.selected.idx)
        reader.Reader(self.cfg, self.selected, self.register, self.deregister) 
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

    @change_selected
    def __next_attr(self, attr, status) :
        cursor = self.selected
        while cursor.next:
            if getattr(cursor.next, attr)() == status:
                self.selected = cursor.next
                break
            cursor = cursor.next

    @change_selected
    def __prev_attr(self, attr, status) :
        cursor = self.selected
        while cursor.prev:
            if getattr(cursor.prev, attr)() == status:
                self.selected = cursor.prev
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

    def toggle_mark(self):
        if self.selected.marked() :
            self.selected.unmark()
        else:
            self.selected.mark()

    def toggle_collapse_tag(self):
        self.list[self.selected.feed_idx].collapsed = not self.list[self.selected.feed_idx].collapsed
        self.selected.unselect()
        self.__map_items()
        self.__select_topoftag(self.selected.feed_idx)

    def __collapse_all(self, c):
        for t in self.list:
            t.collapsed = c
        self.__map_items()
        self.__select_topoftag(self.selected.feedidx)

    def set_collapse_all(self):
        self.__collapse_all(1)

    def unset_collapse_all(self):
        self.__collapse_all(0)

    def force_update(self):
        for f in self.cfg.feeds :
            f.time = 1
        return ALARM

    def tag_read(self):
        self.list[self.selected.feed_idx].all_read()

    def all_read(self):
        for t in self.list:
            t.all_read()

    def tag_unread(self):
        self.list[self.selected.feed_idx].all_unread()

    def all_unread(self):
        for t in self.list :
            t.all_unread()

    def quit(self):
        self.deregister()
        return -1
