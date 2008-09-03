# -*- coding: utf-8 -*-

#Canto - ncurses RSS reader
#   Copyright (C) 2008 Jack Miller <jack@codezen.org>
#
#   This program is free software; you can redistribute it and/or modify
#   it under the terms of the GNU General Public License version 2 as 
#   published by the Free Software Foundation.

import signal
import cfg
import locale
import os
import time
import sys
import getopt
import codecs
import curses
import traceback
import utility
import tag
import gui

ONLY_CONF = 1
UPDATE_FIRST = 2
CHECK_NEW = 4
FEED_LIST = 8

def print_usage():
    print "USAGE: canto [-hvgulanDCLF]"
    print "--help      -h        This help."
    print "--version   -v        Print version info."
    print "--gensconf  -g        Only generate server config."
    print "--update    -u        Fetch updates before running."
    print "--list      -l        List configured feeds."
    print "--checkall  -a        Prints number of new items."
    print "--checknew  -n [feed] Prints number of items that are new in feed."
    print ""
    print "--dir       -D [path] Set configuration directory. (~/.canto/)"
    print "--conf      -C [path] Set configuration file. (~/.canto/conf)"
    print "--log       -L [path] Set client log file. (~/.canto/log)"
    print "--fdir      -F [path] Set feed directory. (~/.canto/feeds/)"

class Main():
    def __init__(self):
        MAJOR,MINOR,REV = VERSION_TUPLE

        locale.setlocale(locale.LC_ALL, "")
        
        try :
            optlist, arglist = getopt.getopt(sys.argv[1:], 'hvgaln:D:C:L:S:O:F:u',\
                    ["help","version","gensconf","update","list","checkall",\
                     "checknew=", "dir=", "conf=","log=","fdir="])
        except getopt.GetoptError, e:
            print "Error: %s" % e.msg
            sys.exit(-1)

        for opt, arg in optlist:
            if opt in ["-D", "--dir"]:
                conf_dir = arg
                break
        else:
            conf_dir = os.getenv("HOME") + "/.canto/"

        if conf_dir[-1] != '/' :
            conf_dir += '/'

        log_file = conf_dir + "log"
        conf_file = conf_dir + "conf"
        serv_file = conf_dir + "sconf"
        feed_dir = conf_dir + "feeds/"
        flags = 0 
        
        feed_ct = None

        for opt, arg in optlist :
            if opt in ["-C", "--conf"] :
                conf_file = arg
            elif opt in ["-L","--log"] :
                log_file = arg
            elif opt in ["-F","--fdir"] :
                feed_dir = arg
                if feed_dir[-1] != '/' :
                    feed_dir += '/'
            elif opt in ["-g","--gensconf"] :
                flags |= ONLY_CONF
            elif opt in ["-u","--update"] :
                flags |= UPDATE_FIRST
            elif opt in ["-n","--checknew"] :
                flags |= CHECK_NEW
                feed_ct = arg
            elif opt in ["-a","--checkall"] :
                flags |= CHECK_NEW
            elif opt in ["-l","--list"] :
                flags |= FEED_LIST
            elif opt in ["-h","--help"] :
                print_usage()
                sys.exit(0)
            elif opt in ["-v","--version"] :
                print "Canto v %d.%d.%d" % (MAJOR,MINOR,REV)
                sys.exit(0)

        try :
            self.cfg = cfg.Cfg(conf_file, serv_file, feed_dir)
        except cfg.ConfigError:
            sys.exit(-1)

        if flags & ONLY_CONF:
            sys.exit(0)
        
        if flags & FEED_LIST:
            for f in self.cfg.feeds:
                print f.tag
            sys.exit(0)

        if flags & UPDATE_FIRST:
            utility.silentfork("canto-fetch -Vf " +\
               "-C \"" + serv_file + \
               "\" -F \"" + feed_dir + \
               "\" -L \"" + conf_dir + "slog\"", 1)
            
            self.stories = []
            for f in self.cfg.feeds :
                f.time = 1
                f.tick()
                self.filter_extend(f)


        if flags & CHECK_NEW:
            if feed_ct:
                for f in self.cfg.feeds:
                    if f.tag == feed_ct:
                        print f.unread
                        break
                else:
                    print "Feed not found."
            else:
                count = 0
                for f in self.cfg.feeds:
                    count += f.unread
                print count
            sys.exit(0)

        self.cfg.key_list = utility.conv_key_list(self.cfg.key_list)
        self.cfg.reader_key_list = utility.conv_key_list(self.cfg.reader_key_list)

        self.stories = []
        for f in self.cfg.feeds:
            self.stories.extend(f)

        self.cfg.stdscr = curses.initscr()
        curses.noecho()
        curses.start_color()
        curses.halfdelay(1)
        curses.use_default_colors()

        self.cfg.height, self.cfg.width = self.cfg.stdscr.getmaxyx()

        for i in range(8) :
            f = utility.convcolor(self.cfg.colors[i][0])
            b = utility.convcolor(self.cfg.colors[i][1])
            curses.init_pair(i + 1, f, b)

        tag_list = [tag.Tag(x.tag) for x in self.cfg.feeds]

        self.key_handlers = []
        gui.Gui(self.cfg, self.stories, tag_list, self.push_handler, self.pop_handler)
        signal.signal(signal.SIGWINCH, self.winch)
        signal.signal(signal.SIGALRM, self.alarm)
        signal.alarm(60)

        self.refresh()

        while 1:
            if not len(self.key_handlers):
                break

            t = None
            k = self.cfg.stdscr.getch()

            if k == curses.KEY_RESIZE:
                self.refresh()
                t = (k, 0)
            elif k == 195:
                k2 = c.stdscr.getch()
                if k2 >= 64:
                    t = (k2 - 64, 1)
                else:
                    t = (k, 0)
            elif k != -1:
                t = (k, 0)

            if t:
                r = self.key_handlers[-1].key(t)
                if r == 1:
                    self.key_handlers[-1].refresh()
                elif r == 2:
                    self.key_handlers[-1].next_item()
                    self.key_handlers[-1].reader()
                elif r == 3:
                    self.key_handlers[-1].prev_item()
                    self.key_handlers[-1].reader()
                elif r == 4:
                    self.alarm()

        curses.endwin()

        for feed in self.cfg.feeds:
            if feed.changed:
                feed.todisk()
        print "Flushed to disk."

        sys.exit(0)

    def winch(self, a=None, b=None):
        curses.ungetch(curses.KEY_RESIZE)

    def alarm(self, a=None, b=None):
        delay = 60
        self.stories = []
        for f in self.cfg.feeds:
            f.tick()
            if len(f) == 0:
                delay = 1
            else:
                self.stories.extend(f)

        self.key_handlers[0].alarm(self.stories)
        signal.alarm(delay)
        self.refresh()

    def refresh(self):
        curses.endwin()
        self.cfg.stdscr.refresh()
        self.cfg.height, self.cfg.width = self.cfg.stdscr.getmaxyx()
        self.cfg.stdscr.keypad(1)

        if self.cfg.resize_hook:
            self.cfg.resize_hook(self.cfg)

        for g in self.key_handlers :
            g.refresh()

    def push_handler(self, handler):
        self.key_handlers.append(handler)

    def pop_handler(self):
        self.key_handlers.pop()
        if len(self.key_handlers):
           for h in self.key_handlers:
               h.refresh()

    def filter_extend(self, t):
        if self.cfg.item_filter:
            self.stories.extend(filter(lambda x: self.cfg.item_filter(t,x), t.ufp.entries))
        else:
            self.stories.extend(map(story.Story, t.ufp.entries))
