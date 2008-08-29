#Canto - ncurses RSS reader
#   Copyright (C) 2008 Jack Miller <jack@codezen.org>
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
import getopt
import stat

class Cfg(list):
    """A basic holster for the config and all of its options.
       pass it a log function, a path to the canto-fetch conf and
       a feed directory and it will populate itself with feeds."""

    def __init__(self, log_func, conf, feed_dir, verbose, force):
        list.__init__(self)
        self.verbose = verbose
        self.force = force
        self.path = conf
        self.log = log_func

        self.__safe_mkdir(feed_dir)
        self.feed_dir = feed_dir

        self.handlers = [(re.compile("^add\s\"(.*?)\"\s\"(.*?)\"\s\"([0-9]+?)\"\s\"([0-9]+?)\"\s\"([0-9]+?)\""), self.__add_feed)]

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

    def __add_feed(self, (handle, URL, rate, keep, title_key)):
        self.log("Add Feed %s\n" % handle)
        dir = self.feed_dir + handle.replace("/", " ")
        self.__safe_mkdir(dir)
        self.append(feed.Feed(dir, handle, URL, int(rate), int(keep),\
                self.log, self.verbose, self.force, int(title_key)))

    def cleanup(self):
        handles = [x.path for x in self]
        for i in os.listdir(self.feed_dir):
            i = self.feed_dir + i
            if stat.S_ISDIR(os.stat(i).st_mode):
                if i not in handles:
                    for path in os.listdir(i):
                        os.unlink(i + '/' + path)
                    os.rmdir(i)
            elif i.endswith(".idx") and i[:-4] not in handles:
                os.unlink(i)

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

def print_usage():
    print "USAGE: canto-fetch [-hvfVCFL]"
    print "--help    -h        Print this help."
    print "--version -v        Print version info."
    print "--verbose -V        Print status while updating."
    print "--force   -f        Force update, even if timestamp is too recent."
    print "--conf    -C [path] Set configuration file. (~/.canto/sconf)"
    print "--fdir    -F [path] Set feed directory. (~/.canto/feeds/)"
    print "--log     -L [path] Set log file (~/.canto/slog)"

def main():
    MAJOR,MINOR,REV = VERSION_TUPLE
    
    home = os.getenv("HOME")
    conf = home + "/.canto/sconf"
    path = home + "/.canto/feeds/"
    log_file = home + "/.canto/slog"
    verbose = 0
    force = 0

    try:
        optlist, arglist = getopt.getopt(sys.argv[1:], 'hvfVC:F:L:',\
                ["verbose","conf=","fdir=","log=", "help", "force"])
    except getopt.GetoptError, e:
        print "Error: %s" % e.msg
        sys.exit(-1)

    for opt, arg in optlist:
        if opt in ["-v","--version"]:
            print "Canto-fetch v %d.%d.%d" % (MAJOR,MINOR,REV)
            sys.exit(0)
        if opt in ["-V","--verbose"]:
            verbose = 1
        elif opt in ["-h","--help"]:
            print_usage()
            sys.exit(0)
        elif opt in ["-C", "--conf"]:
            conf = arg
        elif opt in ["-F", "--fdir"]:
            path = arg
            if path[-1] != '/':
                path += '/'
        elif opt in ["-L", "--log"]:
            log_file = arg
        elif opt in ["-f", "--force"]:
            force = 1
    
    log(log_file, "Canto-fetch v %d.%d.%d\n" % (MAJOR,MINOR,REV), "w")
    log(log_file, "Started execution: %s\n" % time.asctime(time.localtime()), "a")
    log_func = lambda x : log(log_file, x, "a")
    
    cfg = Cfg(log_func, conf, path, verbose, force)
    cfg.parse()
    cfg.cleanup()
    
    for f in cfg:
        f.tick()
        
    log_func("Gracefully exiting Canto-fetch.\n")
    sys.exit(0)
