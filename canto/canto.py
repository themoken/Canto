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
    print "USAGE: canto [-hvgulandDCLF]"
    print "--help      -h        This help."
    print "--version   -v        Print version info."
    print "--gensconf  -g        Only generate server config."
    print "--update    -u        Fetch updates before running."
    print "--list      -l        List configured feeds."
    print "--checkall  -a        Prints number of new items."
    print "--checknew  -n [feed] Prints number of items that are new in feed."
    print ""
    print "--delete    -d [feed] Delete feed from filesystem."
    print "--dir       -D [path] Set configuration directory. (~/.canto/)"
    print "--conf      -C [path] Set configuration file. (~/.canto/conf)"
    print "--log       -L [path] Set client log file. (~/.canto/log)"
    print "--fdir      -F [path] Set feed directory. (~/.canto/feeds/)"

def main():
    """The main function is dedicated mostly to reading
    command line arguments. However it's also host to the
    infinite loop that calls Cfg.loop."""

    MAJOR,MINOR,REV = VERSION_TUPLE

    locale.setlocale(locale.LC_ALL, "")
    conf_dir = None
    try :
        optlist, arglist = getopt.getopt(sys.argv[1:], 'hvgaln:d:D:C:L:S:O:F:u',\
                ["help","version","gensconf","update","list","checkall",\
                 "checknew=", "delete=", "dir=", "conf=","log=","fdir="])
    except getopt.GetoptError, e:
        print "Error: %s" % e.msg
        sys.exit(-1)

    for opt, arg in optlist:
        if opt == "-D":
            conf_dir = arg

    if not conf_dir:
        conf_dir = os.getenv("HOME") + "/.canto/"

    elif conf_dir[-1] != '/' : conf_dir += '/'

    columns = 0
    log_file = conf_dir + "log"
    conf_file = conf_dir + "conf"
    serv_file = conf_dir + "sconf"
    feed_dir = conf_dir + "feeds/"
    only_conf = 0
    update_first = 0
    del_feed = None

    new_ct = 0
    feed_ct = None

    feed_list = 0

    for opt, arg in optlist :
        if opt in ["-C", "--conf"] :
            conf_file = arg
        elif opt in ["-d","--delete"] :
            del_feed = arg
        elif opt in ["-L","--log"] :
            log_file = arg
        elif opt in ["-F","--fdir"] :
            feed_dir = arg
            if feed_dir[-1] != '/' :
                feed_dir += '/'
        elif opt in ["-g","--gensconf"] :
            only_conf = 1
        elif opt in ["-u","--update"] :
            update_first = 1
        elif opt in ["-n","--checknew"] :
            feed_ct = arg
            new_ct = 1
        elif opt in ["-a","--checkall"] :
            new_ct = 1
        elif opt in ["-l","--list"] :
            feed_list = 1
        elif opt in ["-h","--help"] :
            print_usage()
            sys.exit(0)
        elif opt in ["-v","--version"] :
            print "Canto v %d.%d.%d" % (MAJOR,MINOR,REV)
            sys.exit(0)

    log(log_file, "Canto v %d.%d.%d\n" % (MAJOR,MINOR,REV), "w")
    log(log_file, "Started execution: %s\n" % time.asctime(time.localtime()), "a")
    log_func = (lambda x : log(log_file, x, "a"))

    try :
        i = cfg.Cfg(log_func, conf_dir, conf_file, serv_file, feed_dir, del_feed, only_conf, update_first, new_ct, feed_ct, feed_list)
    except IndexError:
        print "You must update feeds, try `canto -u`"
        sys.exit(-1)
    except cfg.ConfigError:
        sys.exit(-1)
    except cfg.FeedError:
        print "Feed not found."
        sys.exit(-1)
    except :
        #curses.endwin()
        print "Caught exception."
        traceback.print_exc()
        sys.exit(-1)

    if del_feed:
        print "Feed deleted."
        sys.exit(0)
    elif only_conf:
        print "Server config generated."
        sys.exit(0)
    elif new_ct or feed_list:
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
