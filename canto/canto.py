# -*- coding: utf-8 -*-

#Canto - ncurses RSS reader
#   Copyright (C) 2008 Jack Miller <jack@codezen.org>
#
#   This program is free software; you can redistribute it and/or modify
#   it under the terms of the GNU General Public License version 2 as 
#   published by the Free Software Foundation.

from const import *
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
import canto_fetch

def print_canto_usage():
    print "USAGE: canto [-hvulanDCLF]"
    print "--help      -h        This help."
    print "--version   -v        Print version info."
    print "--update    -u        Fetch updates before running."
    print "--list      -l        List configured feeds."
    print "--checkall  -a        Prints number of new items."
    print "--checknew  -n [feed] Prints number of items that are new in feed."
    print ""
    print "--opml      -o        Convert conf to OPML and print to stdout."
    print "--import    -i [path] Add feeds from OPML file to conf."
    print ""
    print_common_usage()

def print_fetch_usage():
    print "USAGE: canto-fetch [-hvVfDCLF]"
    print "--help      -h        This help."
    print "--version   -v        Print version info."
    print "--verbose   -V        Print extra info while running."
    print "--force     -f        Force update, regardless of timeestamps."
    print ""
    print_common_usage()

def print_common_usage():
    print "--dir       -D [path] Set configuration directory. (~/.canto/)"
    print "--conf      -C [path] Set configuration file. (~/.canto/conf)"
    print "--log       -L [path] Set client log file. (~/.canto/log)"
    print "--fdir      -F [path] Set feed directory. (~/.canto/feeds/)"

# Main() encompasses an instance of canto running. It sets up the config 
# object and manages the gui objects 
# (Gui(), Reader(), Input(), Search()). 

# Main() includes the stories[] list, the main class keeps that list up to
# date with the changes on disk every minute. The gui classes then update
# based on the new list.

class Main():
    def __init__(self):
        # Let locale figure itself out
        locale.setlocale(locale.LC_ALL, "")
        
        if sys.argv[0].endswith("canto"):
            shortopts = 'hvulaoin:D:C:L:F:'
            longopts =   ["help","version","update","list","checkall","opml",\
                         "import","checknew=", "dir=", "conf=","log=","fdir="]
            iam = "canto"
        elif sys.argv[0].endswith("canto-fetch"):
            shortopts = 'hvVfD:C:L:F:'
            longopts =   ["help","version","verbose","force","dir=",\
                         "conf=", "log=", "fdir="]
            iam = "fetch"
        else:
            print "No idea how you called me..."
            sys.exit(-1)

        try :
            optlist, arglist = getopt.getopt(sys.argv[1:],shortopts,longopts)
        except getopt.GetoptError, e:
            print "Error: %s" % e.msg
            sys.exit(-1)

        # Search the args once for changing the root, because
        # the root directory will effect other options.

        for opt, arg in optlist:
            if opt in ["-D", "--dir"]:
                conf_dir = arg
                break
        else:
            conf_dir = os.getenv("HOME") + "/.canto/"

        if conf_dir[-1] != '/' :
            conf_dir += '/'

        # Now we process the remaining common arguments.
        if iam == "canto":
            log_file = conf_dir + "log"
        else:
            log_file = conf_dir + "fetchlog"

        conf_file = conf_dir + "conf"
        feed_dir = conf_dir + "feeds/"
        
        for opt, arg in optlist :
            if opt in ["-C", "--conf"] :
                conf_file = arg
            elif opt in ["-L","--log"] :
                log_file = arg
            elif opt in ["-F","--fdir"] :
                feed_dir = arg
                if feed_dir[-1] != '/' :
                    feed_dir += '/'
            elif opt in ["-h","--help"] :
                if iam == "canto":
                    print_canto_usage()
                else:
                    print_fetch_usage()
                sys.exit(0)
            elif opt in ["-v","--version"] :
                print "Canto v %d.%d.%d" % VERSION_TUPLE
                sys.exit(0)

        # Instantiate Cfg() using paths in args.

        try :
            self.cfg = cfg.Cfg(conf_file, log_file, feed_dir)
        except cfg.ConfigError:
            sys.exit(-1)
 
        self.cfg.log("Canto v %d.%d.%d" % VERSION_TUPLE, "w")
        self.cfg.log("Time: %s" % time.asctime())
        self.cfg.log("Config parsed successfully.")

        if iam == "fetch":
            sys.exit(canto_fetch.main(self.cfg, optlist))

        flags = 0 
        feed_ct = None
        opml_file = None

        for opt, arg in optlist :
            if opt in ["-u","--update"] :
                flags |= UPDATE_FIRST
            elif opt in ["-n","--checknew"] :
                flags |= CHECK_NEW
                feed_ct = arg
            elif opt in ["-a","--checkall"] :
                flags |= CHECK_NEW
            elif opt in ["-l","--list"] :
                flags |= FEED_LIST
            elif opt in ["-o","--opml"] :
                flags |= OUT_OPML
            elif opt in ["-i","--import"] :
                flags |= IN_OPML
                opml_file = arg

        if flags & IN_OPML:
            self.cfg.source_opml(opml_file, append=True)

        # If self.cfg had to generate a config, make sure we
        # update first.

        if self.cfg.no_conf:
            self.cfg.log("Conf was auto-generated, adding -u")
            flags |= UPDATE_FIRST

        if flags & UPDATE_FIRST:
            self.cfg.log("Pausing to update...")
            canto_fetch.main(self.cfg, [], True, True)

        # Print out a feed list, bail
        if flags & FEED_LIST:
            for f in self.cfg.feeds:
                print f.tag
            sys.exit(0)

        self.stories = []

        # Detect if there are any new feeds by whether their
        # set path exists. If not, run canto-fetch but don't
        # force it, so canto-fetch intelligently updates.

        for f in self.cfg.feeds :
            if not os.path.exists(f.path):
                self.cfg.log("Detected unfetched feed: %s" % f.tag)
                canto_fetch.main(self.cfg, [], True, False)
                self.cfg.log("Fetched.")
                break

        # Force an update from disk
        self.cfg.log("Populating feeds...")
        for f in self.cfg.feeds :
            f.time = 1
            f.tick()
            self.filter_extend(f)

        if flags & OUT_OPML:
            self.cfg.log("Outputting OPML")
            print """<opml version="1.0">"""
            print """<body>"""
            for feed in self.cfg.feeds:
                if not feed.ufp:
                    # This is only reached if a lock wasn't obtained,
                    # in this case, don't even make a guess.
                    print """\t<outline title="%s" xmlUrl="%s" />""" %\
                        (feed.tag, feed.URL)
                    continue
                elif "atom" in feed.ufp["version"]:
                    type = "pie"
                else:
                    type = "rss"

                print """\t<outline title="%s" xmlUrl="%s" type="%s" />""" %\
                        (feed.tag, feed.URL, type)

            print """</body>"""
            print """</opml>"""
            sys.exit(0)

        # Handle -a/-n flags (print number of new items)

        if flags & CHECK_NEW:
            if feed_ct:
                for f in self.cfg.feeds:
                    if f.tag == feed_ct:
                        print f.unread
                        break
                else:
                    print "Feed not found."
            else:
                print sum([f.unread for f in self.cfg.feeds])
            sys.exit(0)


        # At this point we know that we're going to actually launch
        # the client, so we fire up ncurses and add the screen
        # information to our Cfg().

        self.cfg.stdscr = curses.initscr()
        curses.noecho()
        curses.start_color()
        curses.halfdelay(1)
        curses.use_default_colors()
        self.resize = 0

        self.cfg.height, self.cfg.width = self.cfg.stdscr.getmaxyx()

        # Init colors
        for i in range(8) :
            f = utility.convcolor(self.cfg.colors[i][0])
            b = utility.convcolor(self.cfg.colors[i][1])
            curses.init_pair(i + 1, f, b)

        self.cfg.log("Curses initialized.")
    
        # Key handlers is a stack-like list that contains all "inputs"
        # that can take keys from the user. Generally, this is every
        # graphical class open at a time. The last item being the top
        # window, receiving keys.

        self.key_handlers = []

        # Tag_list is created with an empty tag for each feed. A Feed()
        # is a child class of Tag(), however, new Tags() are created 
        #   A) To ensure that none of the gui classes use feed attributes
        #   B) Because feed() must remember all objects in the feed
        #       regardless of whatever filters are applied.

        tag_list = [tag.Tag(None, x.tag) for x in self.cfg.feeds]

        # Instantiate the base Gui class
        gui.Gui(self.cfg, self.stories, tag_list, self.push_handler, \
                self.pop_handler)

        self.cfg.log("GUI initialized.")

        # Signal handling
        signal.signal(signal.SIGWINCH, self.winch)
        signal.signal(signal.SIGALRM, self.alarm)
        signal.alarm(60)

        self.cfg.log("Signals set.")

        # Initial draw of the screen
        self.refresh()

        # Main program loop, terminated when all handlers have
        # deregistered / exited.

        self.cfg.log("Beginning main loop.")

        while 1:
            if not len(self.key_handlers):
                break

            t = None
            k = self.cfg.stdscr.getch()

            # KEY_RESIZE is the only key not propagated, to
            # keep users from rebinding it and crashing.

            if k == curses.KEY_RESIZE or self.resize:
                self.resize = 0
                self.refresh()
                continue

            # Handle Ctrl pairs
            elif k == 195:
                k2 = c.stdscr.getch()
                if k2 >= 64:
                    t = (k2 - 64, 1)
                else:
                    t = (k, 0)

            # Just a normal key-press
            elif k != -1:
                t = (k, 0)

            # This is a while loop to facilitate KEY_PASSTHRU
            # i.e. if an input (like the reader), doesn't recognize
            # a keybind, it will destroy() itself, and the key
            # is passed the next key_handler.

            # This loop is the only way any of the gui classes
            # communicate with each other. They are otherwise
            # entirely independent.

            if hasattr(self.key_handlers[-1], "keys"):
                if self.key_handlers[-1].keys.has_key(t):
                    actl = self.key_handlers[-1].keys[t]
                else:
                    actl = []
            elif t:
                actl = [t]
            else:
                actl = []

            for a in actl:
                r = self.key_handlers[-1].action(a)
                if r == REFRESH_ALL:
                    self.refresh()
                elif r == ALARM:
                    self.alarm()
                elif r == REDRAW_ALL:
                    self.key_handlers[-1].draw_elements()

        # Kill curses
        curses.endwin()

        self.cfg.log("Curses done.")

        # Make sure we leave the on-disk presence constant
        for feed in self.cfg.feeds:
            while feed.changed:
                feed.todisk()

        self.cfg.log("Flushed to disk.")
        sys.exit(0)

    # The reason KEY_RESIZE is used is that it's unsafe to 
    # do much of anything but set a flag in a signal handler,
    # because data structures could be in half-built states,
    # etc. I'm not sure if Python works around that, but the
    # C programmer in me won't allow me to do it and OpenBSD
    # doesn't even support SIGWINCH, so I won't even count
    # on it.

    def winch(self, a=None, b=None):
        self.resize = 1

    # Alarm is called every minute, a and b are unused, but
    # required as part of a signal handler.

    def alarm(self, a=None, b=None):
        self.stories = []
        for f in self.cfg.feeds:
            f.tick()
            self.filter_extend(f)
        
        # Notify all gui objects of (potentially) new items.
        for handler in self.key_handlers:
            if handler.alarm(self.stories):
                handler.draw_elements()

        # Setup the signal again.
        signal.alarm(60)

    # Refresh should only be called initially, if we have a 
    # resize event, or if it's possible that the terminal has
    # been resized in our absence (eg. we've just gotten
    # control back from a text browser).

    # Refresh generally causes gui objects to rebuild window
    # objects and redraw the screen, causing flicker.

    def refresh(self):
        curses.endwin()
        self.cfg.stdscr.refresh()
        self.cfg.height, self.cfg.width = self.cfg.stdscr.getmaxyx()
        self.cfg.stdscr.keypad(1)

        if self.cfg.resize_hook:
            self.cfg.resize_hook(self.cfg)
        self.cfg.columns = max(self.cfg.columns, 1)

        for g in self.key_handlers :
            g.refresh()

    # These two functions are known as register() and deregister()
    # to the gui objects, and let the Main() class know when a gui
    # object should start or stop receiving input.

    def push_handler(self, handler):
        self.key_handlers.append(handler)

    def pop_handler(self):
        self.key_handlers.pop()
        if len(self.key_handlers):
           for h in self.key_handlers:
               h.refresh()

    # Filter extend extends self.stories with items passing through
    # the global filter. The Feed() objects are never changed.

    def filter_extend(self, t):
        if self.cfg.filterlist[self.cfg.filter_idx]:
            self.stories.extend(filter(lambda x:
                self.cfg.filterlist[self.cfg.filter_idx](t,x), t))
        else:
            self.stories.extend(t)
