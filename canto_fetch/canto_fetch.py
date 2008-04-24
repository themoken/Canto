#!/usr/bin/python

#Canto - ncurses RSS reader
#   Copyright (C) 2007 Jack Miller <jack@codezen.org>
#
#   This program is free software; you can redistribute it and/or modify
#   it under the terms of the GNU General Public License version 2 as 
#   published by the Free Software Foundation.

import sys
import re
import os
import feed
import time
import signal
import errno
import codecs

class Cfg(list):
    """A basic holster for the config and all of its options.
       pass it a log function, a path to the canto-fetch conf and
       a feed directory and it will populate itself with feeds."""

    def __init__(self, log_func, conf, feed_dir):
        list.__init__(self)
        self.path = conf
        self.log = log_func

        self.__safe_mkdir(feed_dir)
        self.feed_dir = feed_dir

        self.handlers = [(re.compile("^add\s\"(.*?)\"\s\"(.*?)\"\s\"([0-9]+?)\"\s\"([0-9]+?)\""), self.__add_feed)]

    def parse(self):
        try:
            fsock = codecs.open(self.path, "r", "UTF-8", "ignore")
            try:
                for line in fsock.readlines():
                    for rgx, f in self.handlers:
                        m = rgx.match(line)
                        if m :
                            f(m.groups())
            finally:
                fsock.close()
        except:
            raise

    def __safe_mkdir(self, path):
        if os.path.exists(path) and os.path.isdir(path):
            return
        os.mkdir(path)

    def __add_feed(self, (handle, URL, rate, keep)):
        self.log("Add Feed %s\n" % handle)
        dir = self.feed_dir + handle
        self.__safe_mkdir(dir)
        self.append(feed.Feed(dir, handle, URL, int(rate), int(keep), self.log))

def log(path, str, mode="a"):
    """Simple append log"""
    try :
        f = codecs.open(path, mode, "UTF-8", "ignore")
        try:
            f.write(str)
        finally:
            f.close()
    except IOError:
        pass

def main():
    MAJOR = 0
    MINOR = 4
    REV = 0

    if len(sys.argv) == 1:
        home = os.getenv("HOME")
        conf = home + "/.canto/sconf"
        path = home + "/.canto/feeds/"
        log_file = home + "/.canto/slog"
    elif len(sys.argv) != 4:
        print "USAGE: canto-fetch <conf file> <feed dir> <log file>"
        sys.exit(-1)
    else :
        conf = sys.argv[1]
        path = sys.argv[2]
        log_file = sys.argv[3]

    log(log_file, "Canto-fetch v %d.%d.%d\n" % (MAJOR,MINOR,REV), "w")
    log(log_file, "Started execution: %s\n" % time.asctime(time.localtime()), "a")
    log_func = lambda x : log(log_file, x, "a")
    
    cfg = Cfg(log_func, conf, path)
    cfg.parse()
    
    for f in cfg:
        f.tick()
        
    log_func("Gracefully exiting Canto-fetch.\n")
    sys.exit(0)
