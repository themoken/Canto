# -*- coding: utf-8 -*-

#Canto - ncurses RSS reader
#   Copyright (C) 2008 Jack Miller <jack@codezen.org>
#
#   This program is free software; you can redistribute it and/or modify
#   it under the terms of the GNU General Public License version 2 as 
#   published by the Free Software Foundation.

# The Main object encompasses a running instance of Canto. It can be divided
# into a number of parts.
#    init
#        if called as canto-fetch jump to canto_fetch.main
#        parse config
#        parse canto specific arguments
#        start work thread
#        load the initial feed data (from thread)
#        do one-off operation flags (like -a, -n, -o, -i, etc.)
#        do basic curses init
#        instantiate Gui class
#    main loop
#        check that Gui is still alive
#        if we're waiting for a process, sleep
#        check for input
#            if no input, check on threads
#                if work done, update screen
#            if input, pass to Gui and interpret return
#                if return implies update, queue up work for thread

from process import ProcessHandler
from utility import Cycle
from cfg.base import get_cfg
from const import *
from gui import Gui

import canto_fetch
import utility
import args
import tag

import traceback
import signal
import locale
import curses
import time
import sys
import os

class Main():
    def __init__(self):
        signal.signal(signal.SIGUSR2, self.debug_out)

        # Let locale figure itself out
        locale.setlocale(locale.LC_ALL, "")
        enc = locale.getpreferredencoding()

        # If we're canto-fetch, jump to that main function
        if sys.argv[0].endswith("canto-fetch"):
            canto_fetch.main(enc)

        # Parse arguments that canto shares with canto-fetch, return
        # a lot of file locations and an optlist that will contain the
        # parsed, but yet unused canto specific arguments.

        conf_dir, log_file, conf_file, feed_dir, script_dir, optlist =\
                args.parse_common_args(enc,
                    "hvulaor:t:i:n:",
                    ["help","version","update","list","checkall","opml",
                        "import=","url=","checknew=","tag="])

        # Instantiate the config and start the log.
        try :
            self.cfg = get_cfg(conf_file, log_file, feed_dir, script_dir)
            self.cfg.parse()
        except :
            traceback.print_exc()
            sys.exit(-1)

        self.cfg.log("Canto v %s (%s)" % \
                ("%d.%d.%d" % VERSION_TUPLE, GIT_SHA), "w")
        self.cfg.log("Time: %s" % time.asctime())
        self.cfg.log("Config parsed successfully.")

        # Default arguments.
        flags = 0 
        feed_ct = None
        opml_file = None
        url = None
        newtag = None

        # Note that every single flag that takes an argument has its
        # argument converted to unicode. Saves a lot of bullshit later.

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

        # Import flags harness the same functions as their config
        # based counterparts, source_opml and source_url.

        if flags & IN_OPML:
            self.cfg.locals['source_opml'](opml_file, append=True)
            print "OPML imported."

        if flags & IN_URL:
            self.cfg.locals['source_url'](url, append=True, tag=newtag)
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
            canto_fetch.run(self.cfg, True, True)

        # Detect if there are any new feeds by whether their
        # set path exists. If not, run canto-fetch but don't
        # force it, so canto-fetch intelligently updates.

        for i,f in enumerate(self.cfg.feeds) :
            if not os.path.exists(f.path):
                self.cfg.log("Detected unfetched feed: %s." % f.URL)
                canto_fetch.run(self.cfg, True, False)

                #Still no go?
                if not os.path.exists(f.path):
                    self.cfg.log("Failed to fetch %s, removing" % f.URL)
                    self.cfg.feeds[i] = None
                else:
                    self.cfg.log("Fetched.\n")
                break

        # Collapse the feed array, if we had to remove some unfetchables.
        self.cfg.feeds = filter(lambda x: x != None, self.cfg.feeds)

        self.new = []
        self.old = []
        self.ph = ProcessHandler(self.cfg)

        # Force an update from disk by queueing a work item for each thread.
        # At this point, we just want to do the portion of the update where the
        # disk is read, so PROC_UPDATE is used.

        self.cfg.log("Populating feeds...")
        for f in self.cfg.feeds:
            self.ph.send((PROC_UPDATE, f.URL, []))
            f.merge(self.ph.recv()[1])
        self.ph.send((PROC_GETTAGS, ))

        fixedtags = self.ph.recv()
        
        signal.signal(signal.SIGCHLD, self.chld)
        self.ph.kill_process()
        for i, f in enumerate(self.cfg.feeds):
            self.cfg.feeds[i].tags = fixedtags[i]

        # Now that the tags have all been straightened out, validate the config.
        # Making sure the tags are unique before validation is important because
        # part of validation is the actual creation of Tag() objects.

        try:
            self.cfg.validate()
        except Exception, err:
            print err
            sys.exit(0)

        # Print out a feed list
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
                ufp = feed.get_ufp()
                if "atom" in ufp["version"]:
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
                unread = 0
                for f in self.cfg.feeds:
                    for s in f:
                        if "read" not in s["canto_state"]:
                            unread += 1
                print unread
            else:
                t = [ f for f in self.cfg.feeds if f.tags[0] == feed_ct ]
                if not t:
                    print "Unknown Feed"
                else:
                    print len([ x for x in t[0] if "read"\
                            not in x["canto_state"]])
            sys.exit(0)

        # After this point, we know that all further operation is going to
        # require all tags to be populated, we queue up the latter 
        # half of the work, to actually filter and sort the items.

        # The reason we clear the feeds first is that only after validation do
        # we know what keys are going to have to be precached, and canto tries
        # hard to conserve items (see feed.merge), so we need to replace all of
        # them with corrected, fresh items from the process that knows about the
        # precache

        for f in self.cfg.feeds:
            del f[:]

        self.ph.start_process(self.cfg)
        self.update(1, self.cfg.feeds, PROC_BOTH)

        # At this point we know that we're going to actually launch
        # the client, so we fire up ncurses and add the screen
        # information to our Cfg().

        self.cfg.stdscr = curses.initscr()
        self.cfg.stdscr.nodelay(1)

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
                curses.use_default_colors()
        except:
                self.cfg.log("Unable to init curses, bailing")
                self.done()

        self.sigusr = 0
        self.resize = 0
        self.alarmed = 1
        self.ticks = 1

        self.cfg.height, self.cfg.width = self.cfg.stdscr.getmaxyx()

        # Init colors
        for i, (fg, bg) in enumerate(self.cfg.colors):
            curses.init_pair(i + 1, fg, bg)

        self.cfg.log("Curses initialized.")
    
        # Instantiate the base Gui class
        self.gui = Gui(self.cfg, self.cfg.tags.cur())

        self.cfg.log("GUI initialized.")

        # Signal handling
        signal.signal(signal.SIGWINCH, self.winch)
        signal.signal(signal.SIGALRM, self.alarm)
        signal.signal(signal.SIGINT, self.done)
        signal.signal(signal.SIGUSR1, self.sigusr)

        self.cfg.log("Signals set.")
        self.estring = None

        # The main loop is wrapped in one huge try...except so that no matter
        # what exception is thrown, we can clean up curses and exit without
        # shitting all over the terminal.

        try:
            # Initial draw of the screen
            self.refresh()

            # Main program loop, terminated when all handlers have
            # deregistered / exited.

            self.cfg.log("Beginning main loop.")

            while 1:
                # Clear the key
                t = None

                # Gui is none if a key returned EXIT
                if not self.gui:
                    break

                # If we've spawned a text-based process (i.e. elinks), then just
                # pause and wait to be awakened by SIGCHLD

                if self.cfg.wait_for_pid:
                    signal.pause()

                # Tick when SIGALRM is received.
                if self.alarmed:
                    self.alarmed = 0
                    self.tick()

                # Deferred update from signal
                if self.sigusr:
                    self.sigusr = 0
                    if "signal" in self.cfg.triggers:
                        self.update()

                # Get the key
                k = self.cfg.stdscr.getch()

                # KEY_RESIZE is the only key not propagated, to
                # keep users from rebinding it and crashing.

                if k == curses.KEY_RESIZE or self.resize:
                    self.resize = 0
                    self.refresh()
                    continue

                # No input, time to check on the threads.

                if k == -1:

                    # Make sure we don't pin the CPU, so if there's no input and
                    # no waiting updates, sleep for awhile.

                    r = self.ph.recv(True, 0.01)
                    if r:
                        feed = [ f for f in self.cfg.feeds if f.URL == r[0]][0]
                        f.time = f.rate

                        old = []
                        for gf, tf, s, l in r[3]:
                            if not l:
                                old.append((gf, tf, s, l))
                                continue
                            for i, oldidx in enumerate(l):
                                l[i] = feed[oldidx]
                            old.append((gf, tf, s, l))

                        feed.merge(r[1])

                        new = []
                        for gf, tf, s, l in r[2]:
                            if not l:
                                new.append((gf, tf, s, None))
                                continue
                            for i, newidx in enumerate(l):
                                l[i] = feed[newidx]
                            new.append((gf, tf, s, l))

                        self.gui.alarm(new, old)
                        self.gui.draw_elements()
                    continue

                # Handle Meta pairs
                elif k == 195:
                    k2 = self.cfg.stdscr.getch()
                    if k2 >= 64:
                        t = (k2 - 64, 1)
                    else:
                        t = (k, 0)

                # Just a normal key-press
                else:
                    t = (k, 0)

                # Key resolves a keypress tuple into a list of actions
                actions = self.gui.key(t)

                # Actions are executed in order, and each return code 
                # is handled in order.

                for a in actions:
                    r = self.gui.action(a)
                    if r == REFRESH_ALL:
                        self.refresh()
                    elif r == UPDATE:
                        self.update()
                    elif r in [REFILTER, RETAG]:
                        self.ph.flush()
                        self.update(1)
                    elif r == TFILTER:
                        # Tag filters shouldn't perform a full update, so we map
                        # the relevant tag to all of the feeds that include that
                        # tag and update them.
                        t = self.gui.sel["tag"]
                        ufds = [ f for f in self.cfg.feeds\
                                if t.tag in f.tags]
                        t.clear()
                        self.update(1, ufds)
                    elif r == REDRAW_ALL:
                        self.gui.draw_elements()
                    elif r == EXIT:
                        self.gui = None
                        break

        except Exception:
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

        # If there was an exception, nicely print it out.
        if self.estring:
            self.cfg.log("\nEXCEPTION:")
            self.cfg.log(self.estring)
            print "Canto exited on an exception.\n"
            print self.estring
            print "Please report this bug. Send your logfile " +\
                "(%s) to jack@codezen.org" % self.cfg.log_file

        # Flush the work thread to make sure no updates are going on.
        self.ph.flush()
        self.ph.sync()
        self.cfg.log("Flushed to disk.")

        self.ph.kill_process()
        self.ph.update.close()
        self.ph.updated.close()
        sys.exit(0)

    # For the most part, it's smart to avoid doing anything but set a flag in an
    # signal handler. CHLD is an exception because the only case in which we do
    # anymore work than just acknowledging the process is dead is when
    # wait_for_pid is set and, in this case the main loop is paused anyway.

    def chld(self, a=None, b=None):
        # I'm not sure why, but SIGCHLD gets called and occasionally, os.wait()
        # then complains about there being no waiting processes.
        try:
            pid,none = os.wait()
        except:
            return

        # If the interface is waiting on this pid to be done,
        # reset the signal and simulate a resize to make sure the window
        # information is still fresh.

        if self.cfg.wait_for_pid == pid:
            self.cfg.wait_for_pid = 0
            signal.signal(signal.SIGALRM, self.alarm)
            signal.signal(signal.SIGWINCH, self.winch)
            self.resize = 1

    # Back to better practices. =)

    def winch(self, a=None, b=None):
        self.resize = 1

    def alarm(self, a=None, b=None):
        self.alarmed = 1

    def sigusr(self, a, b):
        self.sigusr = 1

    # Tick decrements two timers. One for a possible update (if "interval" is a
    # valid update trigger), and one for the message box at the bottom of the
    # interface so that messages don't persist for very long.

    def tick(self, refilter=0):
        # Possible update tick
        self.ticks -= 1
        if self.ticks <= 0:
            if "interval" in self.cfg.triggers:
                for f in self.cfg.feeds:
                    f.time -= 1
                self.update(0, [f for f in self.cfg.feeds if f.time < 0])
            self.ticks = 60

        # Message tick
        self.cfg.msg_tick -= 1
        if self.cfg.msg_tick == 0:
            self.cfg.message(self.cfg.status(self.cfg), 1)

        signal.alarm(1)

    # Update is where the work is queued up for the work thread.
    def update(self, refilter = 0, iter = None, action=PROC_BOTH):

        # Default to updating all feeds that match the gui's current tags
        if iter == None:
            iter = []
            for f in self.cfg.feeds:
                for t in self.gui.tags:
                    if t.tag in f.tags:
                        iter.append(f)
                        break

        for f in iter:

            # If we're not refiltering, compare against the current state of the
            # feed, otherwise we count on the tags being empty.
            self.ph.send(
                    (action, f.URL, f[:],\
                    self.cfg.all_filters.index(self.cfg.filters.cur()),
                    [(t.tag,\
                      self.cfg.all_filters.index(t.filters.cur()),\
                      self.cfg.all_sorts.index(t.sorts.cur()))\
                      for t in self.cfg.tags.cur()],\
                      refilter))

    # Refresh should only be called when it's possible that the screen has
    # changed shape. 

    def refresh(self):
        # Get new self.cfg.{height, width}
        curses.endwin()
        self.cfg.stdscr.touchwin()
        self.cfg.stdscr.refresh()
        self.cfg.stdscr.keypad(1)

        self.cfg.height, self.cfg.width = self.cfg.stdscr.getmaxyx()

        # If there's a resize hook, execute it.
        if self.cfg.resize_hook:
            self.cfg.resize_hook(self.cfg)

        # Make sure we've got a minimum for columns and reader_lines
        self.cfg.columns = max(self.cfg.columns, 1)
        self.cfg.reader_lines = max(self.cfg.reader_lines, 3)

        # Adjust gui_height to compensate for the message at the bottom.
        self.cfg.gui_height = self.cfg.height - self.cfg.msg_height
        self.cfg.gui_width = self.cfg.width

        # Now we interpret the reader_orientation setting from the config to
        # shape the reader area, and adjust other height / width settings
        # accordingly.

        # XXX This logic could be cleaned up...

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

        # Create the message window. This could arguably be crammed into the cfg
        # class itself, however, for logging and messaging, the cfg class is
        # basically just a glorified way to do away with globals =P

        self.cfg.msg = curses.newwin(self.cfg.msg_height,\
                self.cfg.width, self.cfg.height - self.cfg.msg_height, 0)
        self.cfg.msg.bkgdset(curses.color_pair(1))
        self.cfg.msg.erase()
        self.cfg.msg.refresh()

        # Perform the main update update.
        self.gui.refresh()
        self.gui.draw_elements()

    # This also doesn't follow good signal practices, but it's an exception
    # because the backtrace is important.

    def debug_out(self, a=None, b=None):
        f = open("canto_debug_out", "w")
        for l in traceback.format_stack():
            f.write(l)
        f.close()
