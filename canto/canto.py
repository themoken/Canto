# -*- coding: utf-8 -*-

#Canto - ncurses RSS reader
#   Copyright (C) 2008 Jack Miller <jack@codezen.org>
#
#   This program is free software; you can redistribute it and/or modify
#   it under the terms of the GNU General Public License version 2 as 
#   published by the Free Software Foundation.

from const import *
from gui import Gui
from utility import Cycle

import canto_fetch
import utility
import cfg
import tag

import traceback
import signal
import locale
import curses
import getopt
import time
import sys
import os

def print_canto_usage():
    print "USAGE: canto [-hvulaniortDCLF]"
    print "--help      -h        This help."
    print "--version   -v        Print version info."
    print "--update    -u        Fetch updates before running."
    print "--list      -l        List configured feeds."
    print "--checkall  -a        Prints number of new items."
    print "--checknew  -n [feed] Prints number of items that are new in feed."

    print ""
    print "--opml      -o        Convert conf to OPML and print to stdout."
    print "--import    -i [path] Add feeds from OPML file to conf."
    print "--url       -r [url]  Add feed at URL to conf."
    print "--tag       -t [tag]  Set tag (for -r)"
    print ""
    print_common_usage()

def print_fetch_usage():
    print "USAGE: canto-fetch [-hvVfdbDCLF]"
    print "--help       -h       This help."
    print "--version    -v       Print version info."
    print "--verbose    -V       Print extra info while running."
    print "--force      -f       Force update, regardless of timeestamps."
    print "--daemon     -d       Run as a daemon."
    print "--background -b       Background (implies -d)"
    print ""
    print_common_usage()

def print_common_usage():
    print "--dir       -D [path] Set configuration directory. (~/.canto/)"
    print "--conf      -C [path] Set configuration file. (~/.canto/conf)"
    print "--log       -L [path] Set client log file. (~/.canto/log)"
    print "--fdir      -F [path] Set feed directory. (~/.canto/feeds/)"
    print "--sdir      -S [path] Set script directory (~/.canto/scripts/)"

# The Main class encompasses a single instance of Canto or Canto-fetch
# running. It handles arguments and parses the config for both binaries.

class Main():
    def __init__(self):
        # Let locale figure itself out
        locale.setlocale(locale.LC_ALL, "")
        enc = locale.getpreferredencoding()

        # Figure out which binary we are, canto or canto-fetch
        # and determine which arguments we'll accept.

        if sys.argv[0].endswith("canto"):
            shortopts = 'hvulaor:t:i:n:D:C:L:F:S:'
            longopts = ["help","version","update","list","checkall","opml",\
                    "import=","url=","checknew=","dir=",\
                    "conf=","log=","fdir=","sdir=", "tag="]

            iam = "canto"
        elif sys.argv[0].endswith("canto-fetch"):
            shortopts = 'hvVfdbD:C:L:F:S:'
            longopts =   ["help","version","verbose","force","dir=",\
                         "conf=", "log=", "fdir=","sdir=",\
                         "daemon","background"]

            iam = "fetch"
        else:
            print "No idea how you called me..."
            sys.exit(-1)

        # Parse the args.

        try :
            optlist = getopt.getopt(sys.argv[1:],shortopts,longopts)[0]
        except getopt.GetoptError, e:
            print "Error: %s" % e.msg
            sys.exit(-1)

        # Canto and canto-fetch share a certain number of args,
        # mainly the ones dealing with locations of a number of
        # directories and files. These args are all capitalized.

        # Search the args once for changing the root, because
        # the root directory will effect other options.

        for opt, arg in optlist:
            if opt in ["-D", "--dir"]:
                conf_dir = unicode(arg, enc, "ignore")
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
        script_dir = conf_dir + "scripts/"

        for opt, arg in optlist :
            if opt in ["-C", "--conf"] :
                conf_file = unicode(arg, enc, "ignore")
            elif opt in ["-L","--log"] :
                log_file = unicode(arg, enc, "ignore")
            elif opt in ["-F","--fdir"] :
                feed_dir = unicode(arg, enc, "ignore")
                if feed_dir[-1] != '/' :
                    feed_dir += '/'
            elif opt in ["-S","--sdir"] :
                script_dir = unicode(arg, enc, "ignore")
                if script_dir[-1] != '/' :
                    script_dir += '/'
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
            self.cfg = cfg.Cfg(conf_file, log_file, feed_dir, script_dir)
            self.cfg.parse()
        except :
            sys.exit(-1)

        self.cfg.log("Canto v %d.%d.%d" % VERSION_TUPLE, "w")
        self.cfg.log("Time: %s" % time.asctime())
        self.cfg.log("Config parsed successfully.")

        if iam == "fetch":
            # Process canto-fetch specific args.

            daemon = False
            background = False
            for opt, arg in optlist :
                if opt in ["-d","--daemon"]:
                    daemon = True
                if opt in ["-b","--background"]:
                    background = True
                    daemon = True

            # Daemonize the process, which is sorta confusing
            # in this context, because daemonizing is running
            # in the background (separate from the shell)
            # Whereas running as a daemon means looping canto-fetch
            # to avoid the need for a crontab.

            if background:
                utility.daemonize()

            if daemon:
                while 1:
                    canto_fetch.main(self.cfg, optlist)
                    time.sleep(60)
                    oldcfg = self.cfg
                    try :
                        self.cfg = cfg.Cfg(conf_file, log_file, feed_dir,\
                                script_dir)
                        self.cfg.parse()
                    except:
                        self.cfg = oldcfg
            sys.exit(canto_fetch.main(self.cfg, optlist))

        # From this point forward, we are definitely canto,
        # not canto-fetch. Begin processing canto specific args.

        flags = 0 
        feed_ct = None
        opml_file = None
        url = None
        newtag = None

        for opt, arg in optlist :
            if opt in ["-u","--update"] :
                flags |= UPDATE_FIRST
            elif opt in ["-n","--checknew"] :
                flags |= CHECK_NEW
                feed_ct = unicode(arg, enc, "ignore")
            elif opt in ["-a","--checkall"] :
                flags |= CHECK_NEW
            elif opt in ["-l","--list"] :
                flags |= FEED_LIST
            elif opt in ["-o","--opml"] :
                flags |= OUT_OPML
            elif opt in ["-i","--import"] :
                flags |= IN_OPML
                opml_file = unicode(arg, enc, "ignore")
            elif opt in ["-r","--url"] :
                flags |= IN_URL
                url = unicode(arg, enc, "ignore")
            elif opt in ["-t","--tag"] :
                newtag = unicode(arg, enc, "ignore")

        if flags & IN_OPML:
            self.cfg.source_opml(opml_file, append=True)
            print "OPML imported."

        if flags & IN_URL:
            self.cfg.source_url(url, append=True, tag=newtag)
            print "URL added."

        # All import options should terminate.

        if flags & (IN_OPML + IN_URL):
            sys.exit(0)

        # If self.cfg had to generate a config, make sure we
        # update first.

        if self.cfg.no_conf:
            self.cfg.log("Conf was auto-generated, adding -u")
            flags |= UPDATE_FIRST

        if flags & UPDATE_FIRST:
            self.cfg.log("Pausing to update...")
            canto_fetch.main(self.cfg, [], True, True)

        # Detect if there are any new feeds by whether their
        # set path exists. If not, run canto-fetch but don't
        # force it, so canto-fetch intelligently updates.

        for i,f in enumerate(self.cfg.feeds) :
            if not os.path.exists(f.path):
                self.cfg.log("Detected unfetched feed: %s." % f.URL)
                canto_fetch.main(self.cfg, [], True, False)

                #Still no go?
                if not os.path.exists(f.path):
                    self.cfg.log("Failed to fetch %s, removing" % f.URL)
                    self.cfg.feeds[i] = None
                else:
                    self.cfg.log("Fetched.\n")
                break

        # Collapse the feed array, if we had to remove some unfetchables.
        self.cfg.feeds = filter(lambda x: x != None, self.cfg.feeds)

        # The stories array is a "hot" list of stories. After the feed
        # filters and the global filters, stories are shunted into this
        # array, regardless of whether they'll be displayed or anything.
        # It isn't until the Gui requests a refresh or a refresh is
        # generated by an interrupt (SIGWINCH/SIGALRM) that these
        # stories may be displayed.

        self.stories = []

        # Force an update from disk
        self.cfg.log("Populating feeds...")
        for f in self.cfg.feeds:
            try:
                f.time = 1
                f.tick()

            # A KeyError is raised by tick() if canto_version on disk
            # doesn't exist or doesn't match the current info.

            except KeyError:
                self.cfg.log("Detected old feed data, forcing update")
                canto_fetch.main(self.cfg, [], True, True)
                f.time = 1
                f.tick()

        base_tags = {}
        for f in [x for x in self.cfg.feeds if x.base_set]:
            otag = f.tags[0]
            if f.tags[0] in base_tags:
                base_tags[otag] += 1
                while f.tags[0] + (" (%d)" % base_tags[otag]) in base_tags:
                    base_tags[otag] += 1
                f.tags[0] += " (%d)" % base_tags[otag]
                for s in f:
                    s.tagwrap(otag, -1)
                    s.tagwrap(f.tags[0], 1)
            else:
                base_tags[f.tags[0]] = 1
            self.filter_extend(f)

        # Print out a feed list, bail
        if flags & FEED_LIST:
            for f in self.cfg.feeds:
                print f.tags[0].encode(enc, "ignore")
            sys.exit(0)

        # This could probably be done better, or more officially
        # with some XML library, but for now, print is working
        # fairly well.

        if flags & OUT_OPML:
            self.cfg.log("Outputting OPML")
            print """<opml version="1.0">"""
            print """<body>"""
            for feed in self.cfg.feeds:
                if "atom" in feed.ufp["version"]:
                    t = "pie"
                else:
                    t = "rss"

                print """\t<outline text="%s" xmlUrl="%s" type="%s" />""" %\
                        (feed.tags[0].encode(enc, "ignore"), feed.URL, t)

            print """</body>"""
            print """</opml>"""
            sys.exit(0)

        # Handle -a/-n flags (print number of new items)

        if flags & CHECK_NEW:
            if not feed_ct:
                feed_ct = "*"

            # We get counts by using the Tag() class directly.
            check_tag = tag.Tag(self.cfg, Cycle([[None]]),\
                    Cycle([None]), feed_ct)
            check_tag.extend(self.stories)
            print check_tag.unread
            sys.exit(0)

        # At this point we know that we're going to actually launch
        # the client, so we fire up ncurses and add the screen
        # information to our Cfg().

        self.cfg.stdscr = curses.initscr()

        # curs_set can return ERR, we shouldn't care
        try:
                curses.curs_set(0)
        except:
                pass

        # if any of these mess up though, the rest of the
        # the operation is suspect, so die.
        try:
                curses.noecho()
                curses.start_color()
                curses.halfdelay(1)
                curses.use_default_colors()
        except:
                self.cfg.log("Unable to init curses, bailing")
                self.done()

        self.resize = 0
        self.alarmed = 0

        self.cfg.height, self.cfg.width = self.cfg.stdscr.getmaxyx()

        # Init colors
        for i in range(8) :
            f = utility.convcolor(self.cfg.colors[i][0])
            b = utility.convcolor(self.cfg.colors[i][1])
            curses.init_pair(i + 1, f, b)

        self.cfg.log("Curses initialized.")
    
        # Instantiate the base Gui class
        self.cfg.validate_tags()
        Gui(self.cfg, self.stories, self.cfg.tags.cur(), \
                self.push_handler, self.pop_handler)

        self.cfg.log("GUI initialized.")

        # Signal handling
        signal.signal(signal.SIGWINCH, self.winch)
        signal.signal(signal.SIGALRM, self.alarm)
        signal.signal(signal.SIGCHLD, self.chld)
        signal.signal(signal.SIGINT, self.done)

        signal.alarm(1)
        self.ticks = 60

        self.cfg.log("Signals set.")
        self.estring = None

        try:
            # Initial draw of the screen
            self.refresh()

            # Main program loop, terminated when all handlers have
            # deregistered / exited.

            self.cfg.log("Beginning main loop.")

            while 1:
                if not len(self.cfg.key_handlers):
                    break

                t = None

                if self.cfg.wait_for_pid:
                    signal.pause()

                k = self.cfg.stdscr.getch()

                # KEY_RESIZE is the only key not propagated, to
                # keep users from rebinding it and crashing.

                if k == curses.KEY_RESIZE or self.resize:
                    self.resize = 0
                    self.refresh()
                    continue

                # Tick when SIGALRM is received.

                if self.alarmed:
                    self.alarmed = 0
                    self.tick()

                # Handle Meta pairs
                elif k == 195:
                    k2 = self.cfg.stdscr.getch()
                    if k2 >= 64:
                        t = (k2 - 64, 1)
                    else:
                        t = (k, 0)

                # Just a normal key-press
                elif k != -1:
                    t = (k, 0)

                if hasattr(self.cfg.key_handlers[self.cfg.cur_kh], "keys"):
                    if t in self.cfg.key_handlers[self.cfg.cur_kh].keys:
                        actl = self.cfg.key_handlers[self.cfg.cur_kh].keys[t]
                    else:
                        actl = []
                elif t:
                    actl = [t]
                else:
                    actl = []

                for a in actl:
                    if not len(self.cfg.key_handlers):
                        self.done()
                    r = self.cfg.key_handlers[self.cfg.cur_kh].action(a)
                    if r == REFRESH_ALL:
                        self.refresh()
                    elif r == ALARM:
                        self.ticks = 1
                        self.tick()
                    elif r == REDRAW_ALL:
                        for k in self.cfg.key_handlers:
                            k.draw_elements()
                    elif r == WINDOW_SWITCH and len(self.cfg.key_handlers) >= 2:
                        oldcur = self.cfg.key_handlers[self.cfg.cur_kh]
                        if self.cfg.cur_kh == len(self.cfg.key_handlers) - 1:
                            self.cfg.cur_kh = 0
                        else:
                            self.cfg.cur_kh += 1
                        self.update_focus()
                        oldcur.draw_elements()
                        self.cfg.key_handlers[self.cfg.cur_kh].draw_elements()
        except Exception:
            # Catch all _non-exit_ exceptions.
            # -> No bug-report message on things like SystemExit.
            self.estring = traceback.format_exc()
        except KeyboardInterrupt:
            pass

        self.done()

    def done(self, a=None, b=None):
        # Unset signals.
        for s in [signal.SIGALRM, signal.SIGWINCH,
                signal.SIGCHLD, signal.SIGINT]:
            signal.signal(s, signal.SIG_IGN)

        # Kill the message log
        self.cfg.msg = None

        # Kill curses
        curses.endwin()

        self.cfg.log("Curses done.")

        if self.estring:
            self.cfg.log("\nEXCEPTION:")
            self.cfg.log(self.estring)
            print "Canto exited on an exception.\n"
            print self.estring
            print "Please report this bug. Send your logfile " +\
                "(%s) to jack@codezen.org" % self.cfg.log_file

        # Make sure we leave the on-disk presence constant
        for feed in self.cfg.feeds:
            while feed.changed:
                feed.todisk()

        self.cfg.log("Flushed to disk.")
        sys.exit(0)

    def chld(self, a=None, b=None):
        try:
            pid,none = os.wait()
        except:
            return
        if self.cfg.wait_for_pid == pid:
            self.cfg.wait_for_pid = 0
            signal.signal(signal.SIGALRM, self.alarm)
            signal.signal(signal.SIGWINCH, self.winch)
            self.resize = 1

    # The reason KEY_RESIZE is used is that it's unsafe to 
    # do much of anything but set a flag in a signal handler,
    # because data structures could be in half-built states,
    # etc. I'm not sure if Python works around that, but the
    # C programmer in me won't allow me to do it and OpenBSD
    # doesn't even support SIGWINCH, so I won't even count
    # on it.

    def winch(self, a=None, b=None):
        self.resize = 1

    # Similarly, alarm is called every minute, and just sets a flag.

    def alarm(self, a=None, b=None):
        self.alarmed = 1

    def tick(self):
        self.ticks -= 1
        if self.ticks <= 0:
            self.stories = []
            for f in self.cfg.feeds:
                f.tick()
                self.filter_extend(f)
    
            for h in self.cfg.key_handlers:
                h.alarm(self.stories)
            self.cfg.key_handlers[self.cfg.cur_kh].refresh()
            self.ticks = 60

        self.cfg.msg_tick -= 1
        if self.cfg.msg_tick == 0:
            self.cfg.message(self.cfg.status(self.cfg), 1)

        signal.alarm(1)

    # Refresh should only be called initially, if we have a 
    # resize event, or if it's possible that the terminal has
    # been resized in our absence (eg. we've just gotten
    # control back from a text browser).

    # Refresh generally causes gui objects to rebuild window
    # objects and redraw the screen, causing flicker.

    def refresh(self):
        curses.endwin()
        self.cfg.stdscr.touchwin()
        self.cfg.stdscr.refresh()
        self.cfg.height, self.cfg.width = self.cfg.stdscr.getmaxyx()

        if self.cfg.resize_hook:
            self.cfg.resize_hook(self.cfg)

        # Make sure we've got a minimum for columns and reader_lines
        self.cfg.columns = max(self.cfg.columns, 1)
        self.cfg.reader_lines = max(self.cfg.reader_lines, 3)

        self.cfg.gui_height = self.cfg.height - self.cfg.msg_height
        self.cfg.gui_width = self.cfg.width

        # This logic could be cleaned up...

        if self.cfg.reader_orientation == "top":
            self.cfg.gui_height -= self.cfg.reader_lines
            self.cfg.gui_top = self.cfg.reader_lines
        elif self.cfg.reader_orientation == "bottom":
            self.cfg.gui_height -= self.cfg.reader_lines
        elif self.cfg.reader_orientation == "left":
            self.cfg.gui_width -= self.cfg.reader_lines
            self.cfg.gui_right = self.cfg.reader_lines
        elif self.cfg.reader_orientation == "right":
            self.cfg.gui_width -= self.cfg.reader_lines
            
        self.cfg.msg = curses.newwin(self.cfg.msg_height,\
                self.cfg.width, self.cfg.height - self.cfg.msg_height, 0)
        self.cfg.msg.bkgdset(curses.color_pair(1))
        self.cfg.msg.erase()
        self.cfg.msg.refresh()

        self.cfg.stdscr.keypad(1)

        for g in self.cfg.key_handlers :
            g.refresh()

    # These two functions are known as register() and deregister()
    # to the gui objects, and let the Main() class know when a gui
    # object should start or stop receiving input.

    def update_focus(self):
        if len(self.cfg.key_handlers):
            for h in self.cfg.key_handlers:
                h.focus = 0
            self.cfg.key_handlers[self.cfg.cur_kh].focus = 1

    def push_handler(self, handler):
        self.cfg.key_handlers.append(handler)
        self.cfg.cur_kh = len(self.cfg.key_handlers) - 1
        self.update_focus()

    def pop_handler(self):
        self.cfg.key_handlers.remove(self.cfg.key_handlers[self.cfg.cur_kh])
        self.cfg.cur_kh = max(self.cfg.cur_kh - 1, 0)
        self.update_focus()
        if len(self.cfg.key_handlers):
           for h in self.cfg.key_handlers:
               h.refresh()

    # Filter extend extends self.stories with items passing through
    # the global filter. The Feed() objects are never changed.

    def filter_extend(self, t):
        filt = self.cfg.filters.cur()
        if filt:
            self.stories.extend(filter(lambda x: filt(t,x), t))
        else:
            self.stories.extend(t)

