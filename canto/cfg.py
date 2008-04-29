# -*- coding: utf-8 -*-

#Canto - ncurses RSS reader
#   Copyright (C) 2007 Jack Miller <jack@codezen.org>
#
#   This program is free software; you can redistribute it and/or modify
#   it under the terms of the GNU General Public License version 2 as 
#   published by the Free Software Foundation.

import os
import sys
import re
import feed
import utility
import codecs
import curses
import gui
import tag
import signal
import interface_draw
import traceback

class ConfigError(Exception):
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)

class Cfg:
    """Cfg() is the class encompassing the configuration of Canto. It contains
    all of the options and functions required to drive the actual GUI. Input
    and signals are all routed to here and dispatched as necessary."""

    def __init__(self, log, conf, sconf, feed_dir, only_conf, update_first):
        self.browser_path = "/usr/bin/firefox \"%u\""
        self.text_browser = 0
        self.render = interface_draw.Renderer()
        self.bin_path = SETUPPY_SET_BIN_PATH
        self.man_path = SETUPPY_SET_MAN_PATH

        self.key_list = {"q" : "quit",
                         "KEY_DOWN" : "next_item",
                         "KEY_UP" : "prev_item",
                         "KEY_NPAGE" : "next_tag",
                         "KEY_PPAGE" : "prev_tag",
                         "g" : "goto",
                         "f" : "inline_search",
                         "F" : "search",
                         "n" : "next_mark",
                         "p" : "prev_mark",
                         " " : "reader",
                         "c" : "toggle_collapse_tag",
                         "C" : "toggle_collapse_all",
                         "m" : "toggle_mark",
                         "r" : "tag_read",
                         "R" : "all_read",
                         "u" : "tag_unread",
                         "U" : "all_unread",
                         "C-r" : "force_update",
                         "C-l" : "refresh",
                         "h" : "help"}
        
        self.reader_key_list = {"KEY_DOWN" : "scroll_down",
                              "KEY_UP" : "scroll_up",
                              "KEY_NPAGE" : "page_down",
                              "KEY_PPAGE" : "page_up",
                              "g" : "goto",
                              "l" : "toggle_show_links"}

        self.colors = [("white","black"),("blue","black"),("yellow","black"),
                ("green","black"),("pink","black"),(0,0),(0,0),(0,0)]

        self.feeds = []
        self.stories = []

        self.default_rate = 5
        self.default_keep = 40

        self.path = conf
        self.sconf = sconf
        self.feed_dir = feed_dir
        self.log = log
        
        self.key_handlers = []
        
        self.columns = 1

        # Start ncurses for two shakes, to get the term's
        # height and width so that the config can 
        # use the info.

        self.stdscr = curses.initscr()
        self.height, self.width = self.stdscr.getmaxyx()
        curses.endwin()

        self.parse()
        self.gen_serverconf()

        if only_conf:
            return

        if len(self.feeds) == 0:
            return

        if update_first:
            print "Pausing to update feeds."
            os.waitpid(utility.silentfork(self.bin_path + "/canto-fetch", 0), 0)
            self.stories = []
            for f in self.feeds :
                f.time = 1
                f.tick()
                self.stories.extend(f)

        self.key_list = self.conv_key_list(self.key_list)
        self.reader_key_list = self.conv_key_list(self.reader_key_list)

        self.stdscr = curses.initscr()
        curses.noecho()
        curses.start_color()
        curses.halfdelay(1)

        # Initialize colors.
        for i in range(8) :
            f = self.convcolor(self.colors[i][0])
            b = self.convcolor(self.colors[i][1])
            curses.init_pair(i + 1, f, b)

        self.height, self.width = self.stdscr.getmaxyx()
        
        try:
            gui.Gui(self, self.height, self.width,self.stories, [tag.Tag(x.handle) for x in self.feeds])
        except IndexError:
            self.destroy()
            raise

        self.refresh()

    def convcolor(self, c):
        colordir = {"black" : 0, 
                "white" : 7, 
                "red" : 1, 
                "green" : 2, 
                "yellow" : 3, 
                "blue" : 4, 
                "magenta" : 5, 
                "pink" : 5, 
                "cyan" : 6}

        if type(c) == int:
            if 0 <= c <= 7:
                return c
            else :
                self.log("Color out of range: %d\n" % (c, ))
                return 0
        elif type(c) == str:
            if colordir.has_key(c):
                return colordir[c]

        self.log("Unknown color: %s\n" % (c, ))
        return 0

    def convkey(self, s):
        """Convert a C-M-x style key to a (key,meta) tuple."""
        if len(s) == 1:
            return (ord(s),0)
        elif s.startswith("C-"):
            k, m = self.convkey(s[2:])
            
            # & 0x1F indicates CTRL status.
            return (k & 0x1F, m) 

        elif s.startswith("M-"):
            k, m = self.convkey(s[2:])
            return (k, 1)

        #For some reason, RETURN isn't in curses
        elif s == "KEY_RETURN":
            return (10, 0)
        else :
            return (getattr(curses, s), 0)

    def conv_key_list(self, dict):
        """Convert a dict with human readable keys to to
           a dict with (key,meta) tuple keys."""

        ret = {}
        for key in dict:
            try:
                newkey = self.convkey(key)
            except AttributeError:
                self.log("%s is not a recognizable key.\n" % (key,))
                continue

            ret[newkey] = dict[key]
        return ret

    def feedwrap(self, handle, URL, **kwargs):
        """A function for export to the config, that makes a feed
        and adds its stories to self.stories appropriately."""

        if kwargs.has_key("keep"):
            keep = kwargs["keep"]
        else :
            keep = self.default_keep

        if kwargs.has_key("rate"):
            rate = kwargs["rate"]
        else :
            rate = self.default_rate

        self.feeds.append(feed.Feed(self, self.feed_dir + handle, handle, URL, rate, keep))
        self.stories.extend(self.feeds[-1])

    def set_default_rate(self, rate):
        """Wrapper to ensure that default_rate is honored by addfeed
        immediately after it's changed."""

        self.default_rate = rate

    def set_default_keep(self, keep):
        """Wrapper to ensure that default_keep is honored by addfeed
        immediately after it's changed."""

        self.default_keep = keep

    def parse(self):
        """Parse the configuration, which exports a number of variables
        to the config which is executable code."""

        locals = {"addfeed":self.feedwrap,
            "height" : self.height,
            "width" : self.width,
            "browser" : self.browser_path,
            "text_browser" : self.text_browser,
            "default_rate" : self.set_default_rate,
            "default_keep" : self.set_default_keep,
            "render" : self.render,
            "renderer" : interface_draw.Renderer,
            "keys" : self.key_list,
            "reader_keys" : self.reader_key_list,
            "columns" : self.columns,
            "colors" : self.colors}

        self.log("Parsing %s\n" % self.path)
        try :
            execfile(self.path, {}, locals)
        except :
            traceback.print_exc()
            raise ConfigError

        # execfile cannot modify basic type
        # locals directly, so we do it by hand.

        self.browser_path = locals["browser"]
        self.text_browser = locals["text_browser"]
        self.render = locals["render"]
        if locals["columns"] > 0:
            self.columns = locals["columns"]

    def gen_serverconf(self):
        """This will output the server configuration corresponding
        to the feeds defined in the client configuration."""

        self.log("Generating server conf to %s\n" % self.sconf)
        try :
            fsock = codecs.open(self.sconf, "w", "UTF-8", "ignore")
            try :
                for f in self.feeds:
                    fsock.write("add \"%s\" \"%s\" \"%d\" \"%d\"\n" \
                            % (f.handle, f.URL, f.rate, f.keep))
            finally :
                fsock.close()
        except IOError:
            pass

    def winch(self, a=None, b=None):
        curses.ungetch(curses.KEY_RESIZE)

    def refresh(self):
        """Refresh is tied to SIGWINCH on Linux, which indicates
        that the terminal has been resized."""

        self.log("Got SIGWINCH\n")

        curses.endwin();
        self.stdscr.refresh();
        self.height, self.width = self.stdscr.getmaxyx()
        self.stdscr.keypad(1)
        for g in self.key_handlers :
            g.refresh(self.height, self.width)

    def loop(self):
        """This is called in an infinite loop from main(),
        blocks on getch() and converts it into a key tuple:
            (key, meta) which is corresponds to keys in either
        of the keylists."""

        if not len(self.key_handlers):
            self.destroy()
            return 1

        k = self.stdscr.getch()
        if k == -1:
            return
        elif k == curses.KEY_RESIZE:
            self.refresh()
            t = (k, 0)
        elif k == 195 :
            k2 = self.stdscr.getch()
            if k2 >= 64:
                t = (k2 - 64, 1)
            else :
                t = (k, 0)
        else :
            t = (k, 0)

        # Pass the vetted key to the last of all handlers.
        self.key_handlers[-1].key(t)

    def alarm(self, a=None, b=None):
        """Called every minute by signal.alarm() in order
        to check the filesystem for updates caused by
        canto-fetch."""

        delay = 60
        self.stories = []
        for f in self.feeds :
            f.tick()
            if len(f) == 0 :
                delay = 1
            self.stories.extend(f)

        self.key_handlers[0].alarm(self.stories)
        signal.alarm(delay)

    def goto(self, URL):
        """Goto() is a wrapper around opening a browser with
        the passed URL. It will silence output from the browser,
        and if needed, surrender the terminal to a text browser."""

        str = re.sub("%u", URL, self.browser_path)
        pid = utility.silentfork(str, self.text_browser)
        if self.text_browser :
            self.alarm()
            self.refresh()

    def pop_handler(self):
        """Remove the last reference to a key_handler, keeping
        it from receiving keys and allowing it to be garbage
        collected."""

        self.key_handlers.pop()
        if len(self.key_handlers):
            for h in self.key_handlers:
                h.refresh(self.height, self.width)

    def destroy(self):
        self.log("Destroying interface.\n")
        curses.endwin()
