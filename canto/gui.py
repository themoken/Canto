# -*- coding: utf-8 -*-

#Canto - ncurses RSS reader
#   Copyright (C) 2008 Jack Miller <jack@codezen.org>
#
#   This program is free software; you can redistribute it and/or modify
#   it under the terms of the GNU General Public License version 2 as 
#   published by the Free Software Foundation.

from input import input, search, num_input
from const import *
import utility
import reader
import extra 

import curses

# Gui() is the class encompassing the basic view of canto,
# the list of feeds (tags) and items.

# Gui()'s main data structure is self.tags, which is a list
# of arbitrary Tag() objects, each being a list of stories.
# A corresponding list is self.map, which maps out the visible
# stories in order of appearance.

# Self.map may seem redundant, but it's mostly for convenience.
# For example, if the items are globally sorted, then iterating
# over self.tags won't work. Or if you're testing membership
# of a story in the self. list (see __select_topoftag).
# Or if your iterating over all visible items (see draw_elements)

# Self.list is still useful though, when dealing with things
# like tag based sorting, or setting the attributes of a Tag()
# since each story doesn't have access to its Tag() object
# directly.

class Gui :
    def __init__(self, cfg, list, tags, register, deregister):
        self.keys = cfg.key_list
        self.window_list = []
        self.map = []
        self.focus = 0

        self.cfg = cfg
        self.register = register
        self.deregister = deregister

        self.lines = 0
        self.sel = 0
        self.sel_idx = -1
        self.items = 0

        self.offset = 0
        self.max_offset = 0

        register(self)

        # Populate the Tag() objects provided with
        # stories from the list given.

        self.tags = tags
        for t in self.tags:
            t.extend(list)
        self.__do_new_hook()

        # Select the first visible feed.

        for t in self.tags :
            if len(t):
                self.sel = t[0]
                self.sel_idx = 0
                t[0].select()
                break
        else:
            self.cfg.log("No Items.")

        if self.cfg.start_hook:
            self.cfg.start_hook(self)

    def __str__(self):
        if self.focus:
            return "%B[base]%b"
        return "[base]"

    def refresh(self):
        # Generate all of the columns
        self.window_list = [curses.newwin(self.cfg.gui_height, \
                    self.cfg.gui_width / self.cfg.columns, \
                    self.cfg.gui_top,\
                    (self.cfg.gui_width / self.cfg.columns) * i\
                    + self.cfg.gui_right) \
                    for i in range(0, self.cfg.columns)]

        # Setup the backgrounds.
        for window in self.window_list:
            window.bkgdset(curses.color_pair(1))

        # Self.lines is the maximum number of visible lines on the screen
        # at any given time. Used for scroll detection.

        self.lines = self.cfg.columns * self.cfg.gui_height

        self.__map_items()
        self.draw_elements()

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
        for i, feed in enumerate(self.tags):
            for item in feed:
                if not feed.collapsed or item.idx == 0:
                    item.lines = item.print_item(self.cfg, feed, 0, self)
                    if item.lines:
                        # item.tag_idx is the story's only reference
                        # to its current Tag()
                        item.tag_idx = i
                        item.row = row
                        row += item.lines
                        self.map.append(item)
        
        self.items = len(self.map)

        # Set max_offset, this is how we know not to recenter the
        # screen when it would leave unused space at the end.
        if self.items:
            self.max_offset = self.map[-1].row + \
                    self.map[-1].lines - self.lines

    def draw_elements(self):
        # Print all stories in self.map
        # Row increments always, because the drawing logic automatically
        # converts a row into a row in the proper window.

        if self.items > 0:
            self.__check_scroll()
            row = -1 * self.offset
            for item in self.map:
                # If row is not offscreen up
                if item.row + item.lines > self.offset:
                    # If row is offscreen down
                    if item.row > self.lines + self.offset:
                        break
                    item.print_item(self.cfg, self.tags[item.tag_idx], row, self)
                row += item.lines
        else:
            row = -1
        
        # Actually perform curses screen update.
        for i,win in enumerate(self.window_list) :
            if i * self.cfg.gui_height >= row:
                win.erase()
            else:
                win.clrtobot()
            win.noutrefresh()
        curses.doupdate()

    def __check_scroll(self) :
        # If our current item is offscreen up, ret 1
        if self.sel.row < self.offset :
            self.offset = self.sel.row
            return 1

        # If our current item is offscreen down, ret 1
        if self.sel.row + self.sel.lines > self.lines + self.offset :
            self.offset = self.sel.row + self.sel.lines - self.lines
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
            if self.sel_idx >= 0:
                if self.cfg.unselect_hook:
                    self.cfg.unselect_hook(self.tags[self.sel.tag_idx],
                            self.sel)
            oldsel = self.sel
            r = fn(self, *args)
            if oldsel:
                oldsel.unselect()
            if self.sel_idx >= 0:
                self.sel = self.map[self.sel_idx]
                self.sel.select()
                if self.cfg.select_hook:
                    self.cfg.select_hook(self.tags[self.sel.tag_idx], self.sel)
            return r
        return dec

    @change_selected
    def alarm(self, listobj):
        # Clear all of the tags and repopulate with the new listobj.
        # At this point, self.sel and self.sel_idx may be invalid

        for t in self.tags:
            t.clear()
            t.extend(listobj)

        self.__do_new_hook()
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

                if self.sel in self.map and \
                        self.map[self.map.index(self.sel)].tag_idx == \
                        self.sel.tag_idx:
                    self.sel_idx = self.map.index(self.sel)
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

    # Use the new_hook on any "new" items.
    # The new attribute is never accessible from the
    # renderer, and is only used for the hook.

    def __do_new_hook(self):
        if self.cfg.new_hook:
            for t in self.tags:
                for item in t:
                    if item.isnew():
                        self.cfg.new_hook(t, item)
                        item.old()

    def action(self, a):
        # Allows user defined functions to manipulate Gui()

        if hasattr(a, "__call__"):
            r = a(self)
        else:
            f = getattr(self, a, None)
            if f:
                r = f()
            else:
                r = -1

        if not r:
            self.draw_elements()
        return r

    @noitem_unsafe
    @change_selected
    def __select_topoftag(self, f=-1):
        if f < 0:
            f = self.sel.tag_idx
        for feed in self.tags[f:]:
            for item in feed:
                if item in self.map:
                    self.sel = item
                    self.sel_idx = self.map.index(self.sel)
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
    def prev_tag(self) :
        curtag = self.sel.tag_idx
        while not self.sel_idx == 0 :
            if curtag != self.sel.tag_idx and self.sel.idx == 0:
                break
            self.prev_item()

    @noitem_unsafe
    def next_tag(self) :
        curtag = self.sel.tag_idx
        while not self.sel_idx == self.items - 1:
            if curtag != self.sel.tag_idx:
                break
            self.next_item()

        # Next_tag should try to keep the top of the tag at
        # the top of the screen (as prev_tag does inherently)
        # so that the user's eye isn't lost.
        self.offset = min(self.sel.row, max(0, self.max_offset))

    # Goto_tagn goes to an absolute #'d tag. So the third
    # tag defined in your configuration will always be '3'

    @noitem_unsafe
    def goto_tag(self, num = None):
        if not num:
            num = num_input(self.cfg, "Absolute Tag")
        if not num:
            return

        if num < 0:
            num = len(self.tags) + num
        num = min(len(self.tags) - 1, num)

        while num > self.sel.tag_idx:
            self.next_tag()
    
        while num < self.sel.tag_idx:
            self.prev_tag()

    # Goto_reltagn goes to a tag relative to what's visible.

    @noitem_unsafe
    def goto_reltag(self, num = None):
        if not num:
            num = num_input(self.cfg, "Tag")
        if not num:
            return

        def rel_search(map):
            idx = -1
            cur = -1
            for item in map:
                if item.tag_idx != cur:
                    cur = item.tag_idx
                    idx += 1
                    if idx == num:
                        break
            return cur

        if num < 0:
            num = -1 * num - 1
            self.goto_tagn(rel_search(reversed(self.map)))
        else:
            self.goto_tagn(rel_search(self.map))

    @noitem_unsafe
    @change_selected
    def next_filtered(self, f) :
        cursor = self.sel_idx + 1
        while not cursor >= self.items:
            if f(self.tags[self.map[cursor].tag_idx],self.map[cursor]):
                self.sel_idx = cursor
                break
            cursor += 1

    @noitem_unsafe
    @change_selected
    def prev_filtered(self, f) :
        cursor = self.sel_idx - 1
        while not cursor < 0:
            if f(self.tags[self.map[cursor].tag_idx],self.map[cursor]):
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
        self.tags[self.sel.tag_idx].set_read(self.sel.idx)

    def just_unread(self):
        self.tags[self.sel.tag_idx].set_unread(self.sel.idx)

    @noitem_unsafe
    def goto(self) :        
        self.tags[self.sel.tag_idx].set_read(self.sel.idx)
        self.draw_elements()
        utility.goto(("", self.sel["link"], "link"), self.cfg)

    def help(self):
        self.cfg.wait_for_pid = utility.silentfork("man canto", "", 1, 0)

    @noitem_unsafe
    def reader(self) :
        self.tags[self.sel.tag_idx].set_read(self.sel.idx)
        reader.Reader(self.cfg, self.sel, self.register, self.deregister) 
        return REDRAW_ALL

    def change_filter(fn):
        def dec(self, *args):
            r,f = fn(self, *args)
            if r:
                self.cfg.log("Filter: %s" % f)
                return self.force_update(0)
        return dec

    @change_filter
    def set_filter(self, filt):
        return (self.cfg.filters.override(filt), self.cfg.filters.cur())

    @noitem_unsafe
    @change_filter
    def set_tag_filter(self, filt):
        return (self.tags[self.sel.tag_idx].filters.override(filt),\
                self.tags[self.sel.tag_idx].filters.cur())

    @change_filter
    def next_filter(self):
        return (self.cfg.filters.next(), self.cfg.filters.cur())
    
    @noitem_unsafe
    @change_filter
    def next_tag_filter(self):
        return (self.tags[self.sel.tag_idx].filters.next(),\
                self.tags[self.sel.tag_idx].filters.cur())

    @change_filter
    def prev_filter(self):
        return (self.cfg.filters.prev(), self.cfg.filters.cur())

    @noitem_unsafe
    @change_filter
    def prev_tag_filter(self):
        return (self.tags[self.sel.tag_idx].filters.prev(),\
                self.tags[self.sel.tag_idx].filters.cur())

    def change_sorts(fn):
        def dec(self, *args):
            r,s = fn(self, *args)
            if r:
                self.cfg.log("Sort: %s" % ", ".join([unicode(x) for x in s]))
                return ALARM
        return dec

    @change_sorts
    def next_tag_sort(self):
        return (self.tags[self.sel.tag_idx].sorts.next(),
                self.tags[self.sel.tag_idx].sorts.cur())

    @change_sorts
    def prev_tag_sort(self):
        return (self.tags[self.sel.tag_idx].sorts.prev(),
                self.tags[self.sel.tag_idx].sorts.cur())

    @change_sorts
    def set_tag_sort(self, sort):
        return (self.tags[self.sel.tag_idx].sorts.override(sort),\
                self.tags[self.sel.tag_idx].sorts.cur())

    def change_tags(fn):
        def dec(self, *args):
            r,t = fn(self, *args)
            if r:
                self.tags = t
                self.cfg.log("Tags: %s" % ", ".join(\
                        [unicode(x) for x in t if x]))
                return ALARM
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
                        story.mark()
                    else:
                        story.unmark()

            self.prev_mark()
            self.next_mark()
            self.draw_elements()

    @noitem_unsafe
    def toggle_mark(self):
        if self.sel.marked() :
            self.sel.unmark()
        else:
            self.sel.mark()

    @noitem_unsafe
    def all_unmarked(self):
        for item in self.map:
            if item.marked():
                item.unmark()

    @noitem_unsafe
    def toggle_collapse_tag(self):
        self.tags[self.sel.tag_idx].collapsed =\
                not self.tags[self.sel.tag_idx].collapsed
        self.sel.unselect()
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

    def force_update(self, v = 1):
        if v:
            self.cfg.log("Forcing update.")

        for f in self.cfg.feeds :
            f.time = 1
        return ALARM
    
    @noitem_unsafe
    def tag_read(self):
        self.tags[self.sel.tag_idx].all_read()

    def all_read(self):
        for t in self.tags:
            t.all_read()

    @noitem_unsafe
    def tag_unread(self):
        self.tags[self.sel.tag_idx].all_unread()

    def all_unread(self):
        for t in self.tags :
            t.all_unread()

    def switch(self):
        return WINDOW_SWITCH

    def quit(self):
        if self.cfg.end_hook:
            self.cfg.end_hook(self)
        self.deregister()
        return -1
