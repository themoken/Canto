# -*- coding: utf-8 -*-

#Canto - ncurses RSS reader
#   Copyright (C) 2008 Jack Miller <jack@codezen.org>
#
#   This program is free software; you can redistribute it and/or modify
#   it under the terms of the GNU General Public License version 2 as 
#   published by the Free Software Foundation.

from input import input, search, num_input
from basegui import BaseGui
from reader import Reader
from const import *
import utility
import extra 

import curses

class Gui(BaseGui) :
    def __init__(self, cfg, tags):
        self.keys = cfg.key_list
        self.window_list = []
        self.map = []
        self.focus = 0
        self.reader_obj = None

        self.cfg = cfg

        self.lines = 0
        self.sel = None
        self.sel_idx = -1
        self.items = 0

        self.offset = 0
        self.max_offset = 0

        self.tags = tags
        self.change_tag_override = 0

        if self.cfg.start_hook:
            self.cfg.start_hook(self)

    def refresh(self):
        # Generate all of the columns
        self.window_list = [curses.newpad(self.cfg.gui_height + 1, \
                    self.cfg.gui_width / self.cfg.columns)\
                    for i in range(0, self.cfg.columns)]

        # Setup the backgrounds.
        for window in self.window_list:
            window.bkgdset(curses.color_pair(1))

        # Self.lines is the maximum number of visible lines on the screen
        # at any given time. Used for scroll detection.

        self.lines = self.cfg.columns * self.cfg.gui_height

        self.__map_items()
        self.draw_elements()
        if self.reader_obj:
            self.reader_obj.refresh()

    def print_item(self, tag, story, row):
        d = { "story" : story, "tag" : tag, "row" : row,\
                "width" : self.cfg.width / self.cfg.columns,
                "window_list" : self.window_list }
        return tag.renderer.story(d)

    def __map_items(self):

        # This for loop populates self.map with all stories that
        #   A - are first in a collapsed feed or not in one at all.
        #   B - that actually manage to print something to the screen.
        
        # Because of B, you can perform filtering in a Renderer().

        # We keep track of the virtual row to keep offsets in line.
        # It doesn't actually map to the row it's printed to on the
        # screen.

        self.map = []
        row = 0
        for i, tag in enumerate(self.tags):
            for item in tag:
                if not tag.collapsed or item.idx == 0:
                    lines = self.print_item(tag, item, 0)
                    if lines:
                        self.map.append(
                            {"tag" : tag,
                             "row" : row,
                             "item" : item,
                             "lines" : lines})
                        row += lines

        self.items = len(self.map)

        # Set max_offset, this is how we know not to recenter the
        # screen when it would leave unused space at the end.
        self.max_offset = row - self.lines

    def draw_elements(self):
        # Print all stories in self.map
        # Row increments always, because the drawing logic automatically
        # converts a row into a row in the proper window.

        if self.items > 0:
            self.__check_scroll()
            row = -1 * self.offset
            for item in self.map:
                # If row is not offscreen up
                if item["row"] + item["lines"] > self.offset:
                    # If row is offscreen down
                    if item["row"] > self.lines + self.offset:
                        break
                    self.print_item(item["tag"], item["item"], row)
                row += item["lines"]
        else:
            row = -1

        # Actually perform curses screen update.
        for i,win in enumerate(self.window_list) :
            if i * self.cfg.gui_height >= row:
                win.erase()
            else:
                win.clrtobot()
            win.noutrefresh(0,0,
                    self.cfg.gui_top,
                    i*(self.cfg.gui_width / self.cfg.columns),
                    self.cfg.gui_height - 1,
                    (i+1)*(self.cfg.gui_width / self.cfg.columns))

        if self.reader_obj:
            self.reader_obj.draw_elements()
        curses.doupdate()

    def key(self, k):
        if self.reader_obj:
            return self.reader_obj.key(k)
        return BaseGui.key(self, k)

    def action(self, a):
        if self.reader_obj:
            return self.reader_obj.action(a)
        r = BaseGui.action(self, a)
        if self.change_tag_override:
            self.change_tag_override = 0
            return ALARM
        return r

    def __check_scroll(self) :
        # If our current item is offscreen up, ret 1
        if self.sel["row"] < self.offset :
            self.offset = self.sel["row"]
            return 1

        # If our current item is offscreen down, ret 1
        if self.sel["row"] + self.sel["lines"] > self.lines + self.offset :
            self.offset = self.sel["row"] + self.sel["lines"] - self.lines
            return 1
        return 0

    # This decorator makes items (usu. keybinds) that require
    # items to be present bail if none are.

    def noitem_unsafe(fn):
        def ns_dec(self, *args):
            if self.items > 0:
                return fn(self, *args)
            else:
                self.cfg.log("No Items.")
        return ns_dec

    # This decorator lets the bind just change sel_idx and
    # have self.sel set automatically and the story's state
    # synced.

    def change_selected(fn):
        def dec(self, *args):
            oldsel = self.sel

            r = fn(self, *args)

            if oldsel:
                oldsel["item"].unselect()
                if self.cfg.unselect_hook:
                    self.cfg.unselect_hook(oldsel["tag"], oldsel["item"])

            if self.sel_idx >= 0:
                self.sel = self.map[self.sel_idx]
                self.sel["item"].select()
                if self.cfg.select_hook:
                    self.cfg.select_hook(self.sel["tag"], self.sel["item"])

            if "change_tag" in self.cfg.triggers and\
                oldsel and self.sel and \
                oldsel["tag"] != self.sel["tag"]:
                    self.change_tag_override = ALARM
            return r
        return dec

    @change_selected
    def alarm(self, new=[], old=[]):
        # Clear all of the tags and repopulate with the new listobj.
        # At this point, self.sel and self.sel_idx may be invalid

        if old:
            for i, l in enumerate(old):
                if l:
                    self.tags[i].retract(l)
        if new:
            for i, l in enumerate(new):
                if l:
                    self.tags[i].extend(l)

        self.__map_items() 

        # sel_idx may no longer be valid, because the item
        # list could shrink arbitrarily.
        self.sel_idx = min(self.sel_idx, self.items - 1)
        
        if self.items > 0:
            # Attempt to update sel_idx, if the item is still
            # visible (in self.map), otherwise just select
            # the top of the current (or first previous feed).

            if self.sel:
                # Since items can show up in multiple feeds
                # (i.e. reddit and subreddits), check that the
                # tag_idx is the same, so we don't jump from one
                # tag to another inadvertently.

                for i, item in enumerate(self.map):
                    if self.sel["item"] == item["item"] and\
                            self.sel["tag"] == item["tag"]:
                        self.sel_idx = i
                        break
                else:
                    self.__select_topoftag()
            else:
                self.__select_topoftag(0)

        # If we had a selection, and now no items notify the user.
        elif self.sel:
            self.cfg.log("No Items.")
            self.sel = None

        if self.cfg.update_hook:
            self.cfg.update_hook(self)

    @noitem_unsafe
    @change_selected
    def __select_topoftag(self, t=-1):
        if t < 0:
            t = self.tags.index(self.sel["tag"])
        for tag in self.tags[t:]:
            for item in tag:
                for i in xrange(len(self.map)):
                    if self.map[i]["item"] == item:
                        self.sel = self.map[i]
                        self.sel_idx = i
                        return

    @change_selected
    def next_item(self):
        if self.sel_idx < self.items - 1:
            self.sel_idx += 1

    @change_selected
    def prev_item(self):
        if self.sel_idx > 0 :
            self.sel_idx -= 1

    @noitem_unsafe
    def prev_tag(self):
        curtag = self.sel["tag"]
        while not self.sel_idx == 0 :
            if curtag != self.sel["tag"] and \
                    self.sel["item"] == self.sel["tag"][0]:
                break
            self.prev_item()

    @noitem_unsafe
    def next_tag(self):
        curtag = self.sel["tag"]
        while not self.sel_idx == self.items - 1:
            if curtag != self.sel["tag"]:
                break
            self.next_item()

        # Next_tag should try to keep the top of the tag at
        # the top of the screen (as prev_tag does inherently)
        # so that the user's eye isn't lost.
        self.offset = min(self.sel["row"], max(0, self.max_offset))

    # Goto_tagn goes to an absolute #'d tag. So the third
    # tag defined in your configuration will always be '3'

    @noitem_unsafe
    def goto_tag(self, num = None):
        if not num:
            num = num_input(self.cfg, "Absolute Tag")
        if num == None:
            return

        if num < 0:
            num = len(self.tags) + num
        num = min(len(self.tags) - 1, num)
 
        idx = self.tags.index(self.sel["tag"])
        while num != idx:
            if num > idx:
                self.next_tag()
            elif num < idx:
                self.prev_tag()
            idx = self.tags.index(self.sel["tag"])

    # Goto_reltagn goes to a tag relative to what's visible.

    @noitem_unsafe
    def goto_reltag(self, num = None):
        if not num:
            num = num_input(self.cfg, "Tag")
        if not num:
            return

        def rel_search(map):
            idx = -1
            cur = None
            for item in map:
                if item["tag"] != cur:
                    cur = self.tags.index(item["tag"])
                    idx += 1
                    if idx == num:
                        break
            return cur

        if num < 0:
            num = -1 * num - 1
            self.goto_tag(rel_search(reversed(self.map)))
        else:
            self.goto_tag(rel_search(self.map))

    @noitem_unsafe
    @change_selected
    def next_filtered(self, f) :
        cursor = self.sel_idx + 1
        while not cursor >= self.items:
            if f(self.map[cursor]["tag"],self.map[cursor]["item"]):
                self.sel_idx = cursor
                break
            cursor += 1

    @noitem_unsafe
    @change_selected
    def prev_filtered(self, f) :
        cursor = self.sel_idx - 1
        while not cursor < 0:
            if f(self.map[cursor]["tag"],self.map[cursor]["item"]):
                self.sel_idx = cursor
                break
            cursor -= 1

    def next_mark(self):
        self.next_filtered(extra.show_marked())

    def prev_mark(self):
        self.prev_filtered(extra.show_marked())

    def next_unread(self):
        self.next_filtered(extra.show_unread())

    def prev_unread(self):
        self.prev_filtered(extra.show_unread())

    def just_read(self):
        self.sel["tag"].set_read(self.sel["item"])

    def just_unread(self):
        self.sel["tag"].set_unread(self.sel["item"])

    @noitem_unsafe
    def goto(self) :        
        self.sel["tag"].set_read(self.sel["item"])
        self.draw_elements()
        utility.goto(("", self.sel["item"]["link"], "link"), self.cfg)

    def help(self):
        self.cfg.wait_for_pid = utility.silentfork("man canto", "", 1, 0)

    @noitem_unsafe
    def reader(self) :
        self.sel["tag"].set_read(self.sel["item"])
        self.reader_obj = Reader(self.cfg, self.sel["tag"],\
                self.sel["item"], self.reader_dead)
        return REDRAW_ALL

    def reader_dead(self):
        self.reader_obj = None

    def change_filter(fn):
        def dec(self, *args):
            r,f = fn(self, *args)
            if r:
                self.cfg.log("Filter: %s" % f)
                for t in self.tags:
                    t.clear()
                return REFILTER
        return dec

    @change_filter
    def set_filter(self, filt):
        return (self.cfg.filters.override(filt), self.cfg.filters.cur())

    @noitem_unsafe
    @change_filter
    def set_tag_filter(self, filt):
        return (self.sel["tag"].filters.override(filt),\
                self.sel["tag"].filters.cur())

    @change_filter
    def next_filter(self):
        return (self.cfg.filters.next(), self.cfg.filters.cur())
    
    @noitem_unsafe
    @change_filter
    def next_tag_filter(self):
        return (self.sel["tag"].filters.next(),\
                self.sel["tag"].filters.cur())

    @change_filter
    def prev_filter(self):
        return (self.cfg.filters.prev(), self.cfg.filters.cur())

    @noitem_unsafe
    @change_filter
    def prev_tag_filter(self):
        return (self.sel["tag"].filters.prev(),\
                self.sel["tag"].filters.cur())

    def change_sorts(fn):
        def dec(self, *args):
            r,s = fn(self, *args)
            if r:
                self.cfg.log("Sort: %s" % ", ".join([unicode(x) for x in s]))
                return ALARM
        return dec

    @noitem_unsafe
    @change_sorts
    def next_tag_sort(self):
        return (self.sel["tag"].sorts.next(),
                self.sel["tag"].sorts.cur())

    @noitem_unsafe
    @change_sorts
    def prev_tag_sort(self):
        return (self.sel["tag"].sorts.prev(),
                self.sel["tag"].sorts.cur())

    @noitem_unsafe
    @change_sorts
    def set_tag_sort(self, sort):
        return (self.sel["tag"].sorts.override(sort),\
                self.sel["tag"].sorts.cur())

    def change_tags(fn):
        def dec(self, *args):
            r,t = fn(self, *args)
            if r:
                for ot in self.tags:
                    ot.clear()
                self.tags = t
                self.sel = None
                self.cfg.log("Tags: %s" % ", ".join([unicode(x) for x in t]))
                return RETAG
        return dec

    @change_tags
    def next_tagset(self):
        return (self.cfg.tags.next(), self.cfg.tags.cur())

    @change_tags
    def prev_tagset(self):
        return (self.cfg.tags.prev(), self.cfg.tags.cur())

    @change_tags
    def set_tagset(self, t):
        return (1, self.cfg.get_real_tagl(t))

    @noitem_unsafe
    def inline_search(self):
        self.do_inline_search(search(self.cfg, "Inline Search"))

    def do_inline_search(self, s) :
        if s:
            for t in self.tags:
                for story in t:
                    if s.match(story["title"]):
                        story.set("marked")
                    else:
                        story.unset("marked")

            self.prev_mark()
            self.next_mark()
            self.draw_elements()

    @noitem_unsafe
    def toggle_mark(self):
        if self.sel["item"].was("marked"):
            self.sel["item"].unset("marked")
        else:
            self.sel["item"].set("marked")

    @noitem_unsafe
    def all_unmarked(self):
        for item in self.map:
            if item["item"].was("marked"):
                item["item"].unset("marked")

    @noitem_unsafe
    def toggle_collapse_tag(self):
        self.sel["tag"].collapsed =\
                not self.sel["tag"].collapsed
        self.sel["item"].unselect()
        self.__map_items()
        self.__select_topoftag()

    def __collapse_all(self, c):
        for t in self.tags:
            t.collapsed = c
        self.__map_items()
        self.__select_topoftag()

    def set_collapse_all(self):
        self.__collapse_all(1)

    def unset_collapse_all(self):
        self.__collapse_all(0)

    def force_update(self):
        self.cfg.log("Forcing update.")
        for f in self.cfg.feeds :
            f.time = 1
        return ALARM
    
    @noitem_unsafe
    def tag_read(self):
        self.sel["tag"].all_read()

    def all_read(self):
        for t in self.tags:
            t.all_read()

    @noitem_unsafe
    def tag_unread(self):
        self.sel["tag"].all_unread()

    def all_unread(self):
        for t in self.tags :
            t.all_unread()

    def quit(self):
        if self.cfg.end_hook:
            self.cfg.end_hook(self)
        return EXIT
