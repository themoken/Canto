# -*- coding: utf-8 -*-

#Canto - ncurses RSS reader
#   Copyright (C) 2008 Jack Miller <jack@codezen.org>
#
#   This program is free software; you can redistribute it and/or modify
#   it under the terms of the GNU General Public License version 2 as 
#   published by the Free Software Foundation.

# This is probably the most straightforward file in the code base. It handles
# all of the argument parsing and interprets all of the common arguments between
# canto and canto-fetch.

# The one thing to note is that every option that is parsed with an actual
# argument must have that argument converted to unicode right off the bat.

from const import *
import getopt
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
    print "--interval   -i       Update interval when run as a daemon"
    print ""
    print_common_usage()

def print_common_usage():
    print "--dir       -D [path] Set configuration directory. (~/.canto/)"
    print "--conf      -C [path] Set configuration file. (~/.canto/conf)"
    print "--log       -L [path] Set client log file. (~/.canto/log)"
    print "--fdir      -F [path] Set feed directory. (~/.canto/feeds/)"
    print "--sdir      -S [path] Set script directory (~/.canto/scripts/)"

def parse_common_args(enc, extra_short, extra_long, iam="canto"):
    shortopts = 'D:C:L:F:S:' + extra_short
    longopts = ["dir=","conf=","log=","fdir=","sdir="] + extra_long

    try :
        optlist = getopt.getopt(sys.argv[1:],shortopts,longopts)[0]
    except getopt.GetoptError, e:
        print "Error: %s" % e.msg
        sys.exit(-1)

    for opt, arg in optlist:
        if opt in ["-D", "--dir"]:
            conf_dir = unicode(arg, enc, "ignore")
            break
    else:
        conf_dir = os.getenv("HOME") + "/.canto/"

    if conf_dir[-1] != '/' :
        conf_dir += '/'

    if not os.path.exists(conf_dir):
        os.mkdir(conf_dir)

    if iam == "canto":
        log_file = conf_dir + "log"
    else:
        log_file = conf_dir + "fetchlog"

    conf_file = conf_dir + "conf.py"
    feed_dir = conf_dir + "feeds/"
    script_dir = conf_dir + "scripts/"

    # Make sure that the {feed,script}_dir does, indeed, exist and is
    # actually a directory.

    for dir in [feed_dir, script_dir]:
        if not os.path.exists(dir):
            os.mkdir(dir)
        elif not os.path.isdir(dir):
            os.unlink(dir)
            os.mkdir(dir)

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
            print "Canto v %s (%s)" % ("%d.%d.%d" % VERSION_TUPLE, GIT_SHA)
            sys.exit(0)

    return (conf_dir, log_file, conf_file, feed_dir, script_dir, optlist)
