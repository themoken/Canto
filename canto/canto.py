# -*- coding: utf-8 -*-

#Canto - ncurses RSS reader
#   Copyright (C) 2007 Jack Miller <jack@codezen.org>
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

def log(path, str, mode="a"):
    try :
        f = codecs.open(path, mode, "UTF-8", "ignore")
        try:
            f.write(str)
        finally:
            f.close()
    except IOError:
        pass

def print_usage():
    print "USAGE: canto [-hvguDCLF]"
    print "  -h        This help."
    print "  -v        Print version info."
    print "  -g        Only generate server config."
    print "  -u        Fetch updates before running."
    print "  -d [feed] Delete feed from filesystem."
    print "  -D [path] Set configuration directory. (~/.canto/)"
    print "  -C [path] Set configuration file. (~/.canto/conf)"
    print "  -L [path] Set client log file. (~/.canto/log)"
    print "  -F [path] Set feed directory. (~/.canto/feeds/)"

def main():
    """The main function is dedicated mostly to reading
    command line arguments. However it's also host to the
    infinite loop that calls Cfg.loop."""

    MAJOR = 0
    MINOR = 4
    REV = 0

    locale.setlocale(locale.LC_ALL, "")
    conf_dir = None
    try :
        optlist, arglist = getopt.getopt(sys.argv[1:], 'hvgd:D:C:L:S:O:F:u')
    except getopt.GetoptError, e:
        print "Error: %s" % e.msg
        sys.exit(-1)

    for opt, arg in optlist :
        if opt == "-D" : conf_dir = arg

    if not conf_dir : conf_dir = os.getenv("HOME") + "/.canto/"
    elif conf_dir[-1] != '/' : conf_dir += '/'

    columns = 0
    log_file = conf_dir + "log"
    conf_file = conf_dir + "conf"
    serv_file = conf_dir + "sconf"
    feed_dir = conf_dir + "feeds/"
    only_conf = 0
    update_first = 0
    del_feed = None

    for opt, arg in optlist :
        if opt == "-C" :
            conf_file = arg
        elif opt == "-d":
            del_feed = arg
        elif opt == "-L" :
            log_file = arg
        elif opt == "-F" :
            feed_dir = arg
            if feed_dir[-1] != '/' :
                feed_dir += '/'
        elif opt == "-g" :
            only_conf = 1
        elif opt == "-u" :
            update_first = 1
        elif opt == "-h" :
            print_usage()
            sys.exit(0)
        elif opt == "-v" :
            print "Canto v %d.%d.%d" % (MAJOR,MINOR,REV)
            sys.exit(0)

    log(log_file, "Canto v %d.%d.%d\n" % (MAJOR,MINOR,REV), "w")
    log(log_file, "Started execution: %s\n" % time.asctime(time.localtime()), "a")
    log_func = (lambda x : log(log_file, x, "a"))

    try :
        i = cfg.Cfg(log_func, conf_file, serv_file, feed_dir, del_feed, only_conf, update_first)
    except IndexError:
        print "You must update feeds, try `canto -u`"
        sys.exit(-1)
    except cfg.ConfigError:
        sys.exit(-1)
    except :
        curses.endwin()
        print "Caught exception."
        traceback.print_exc()
        sys.exit(-1)

    if only_conf:
        print "Server config generated."
        sys.exit(0)
    elif len(i.feeds) <= 0 :
        print "You have to add some feeds! Read `man canto`"
        sys.exit(-1)

    signal.signal(signal.SIGALRM, i.alarm)
    signal.signal(signal.SIGWINCH, i.winch)
    signal.signal(signal.SIGTTOU, signal.SIG_IGN)
    signal.alarm(1)

    while 1 :
        if i.loop() :
            break

    sys.exit(0)
