# -*- coding: utf-8 -*-

#Canto - ncurses RSS reader
#   Copyright (C) 2008 Jack Miller <jack@codezen.org>
#
#   This program is free software; you can redistribute it and/or modify
#   it under the terms of the GNU General Public License version 2 as 
#   published by the Free Software Foundation.

import tempfile
import urllib2
import signal 
import curses
import sys
import re
import os

# The Cycle class has proved to be useful. It's used
# to encapsulate every cycle in canto, global filters,
# tag filters, global and tag sorts, tags. It's
# essentially a list with a current pointer and
# exception proof next/prev function and the ability
# to temporarily override a particular value.

class Cycle():
    def __init__(self, list, idx = 0):
        self.over = None
        self.list = list
        if 0 <= idx < len(self.list):
            self.idx = idx
        else:
            self.idx = 0

    def next(self):
        self.over = None
        if self.idx >= len(self.list) - 1:
            return 0
        self.idx += 1
        return 1

    def prev(self):
        self.over = None
        if self.idx <= 0:
            return 0
        self.idx -= 1
        return 1

    def override(self, cur):
        if self.over != cur:
            self.over = cur
            return 1
        return 0

    def cur(self):
        return self.over or self.list[self.idx]

# The get_instance() and get_list_of_instances()
# functions are to ensure that all objects (usu.
# in a Cfg()) are actual, instantiated objects and
# not just references.

def get_instance(l):
    if not l:
        return l
    return (hasattr(l, "__class__") and l) or l()

def get_list_of_instances(l):
    if not hasattr(l, "__iter__"):
        l = [l]

    r = []
    for i in l:
        if hasattr(i, "__iter__"):
            r.append(get_list_of_instances(i))
        else:
            r.append(get_instance(i))
    return r

def daemonize():
    pid = os.fork()
    if not pid:
        # New terminal session
        os.setsid()

        os.chdir("/")
        os.umask(0)
        pid = os.fork()
        if pid:
            sys.exit(0)
    else:
        sys.exit(0)

    # Close all possible terminal output
    # file descriptors. 

    os.close(0)
    os.close(1)
    os.close(2)

def convcolor(c):
    colordir = {"default" : -1, 
            "black" : 0, 
            "white" : 7, 
            "red" : 1, 
            "green" : 2, 
            "yellow" : 3, 
            "blue" : 4, 
            "magenta" : 5, 
            "pink" : 5, 
            "cyan" : 6}

    if type(c) == int:
        if 0 <= c <= curses.COLORS:
            return c
        else:
            return 0
    elif type(c) == str:
        if c in colordir:
            return colordir[c]
    return 0

def convkey(s):
    if len(s) == 1:
        return (ord(s),0)
    elif s.startswith("C-"):
        k, m = convkey(s[2:])
        
        # & 0x1F indicates CTRL status.
        return (k & 0x1F, m) 

    elif s.startswith("M-"):
        k, m = self.convkey(s[2:])
        return (k, 1)

    #For some reason, RETURN isn't in curses
    elif s == "KEY_RETURN":
        return (10, 0)
    else:
        return (getattr(curses, s), 0)

def conv_key_list(dict):
    ret = {}
    for key in dict:
        if not dict[key]:
            continue

        try:
            newkey = convkey(key)
        except AttributeError:
            continue

        # All the items in a key_list must be lists.
        if type(dict[key]) != type([]):
            ret[newkey] = [dict[key]]
        else:
            ret[newkey] = dict[key]

    return ret

def silentfork(path, href, text, fetch):

    pid = os.fork()
    if not pid :
        # A lot of programs don't appreciate
        # having their fds closed, so instead
        # we dup them to /dev/null.

        fd = os.open("/dev/null", os.O_RDWR)
        os.dup2(fd, sys.stderr.fileno())

        if not text:
            os.setpgid(os.getpid(), os.getpid())
            os.dup2(fd, sys.stdout.fileno())

        if fetch:
            response = urllib2.urlopen(href)
            data = response.read()
            fd, name = tempfile.mkstemp()
            os.write(fd, data)
            os.close(fd)
            path = path.replace("%u", name)
        else:
            path = path.replace("%u", href)

        os.system(path)
        sys.exit(0)

    if text:
        signal.signal(signal.SIGALRM, signal.SIG_IGN)
        signal.signal(signal.SIGWINCH, signal.SIG_IGN)

    return pid

def goto(link, cfg):
    title,href,handler = link
    if handler in cfg.handlers:
        for k in [h for h in cfg.handlers[handler].keys() if h]:
            if href.endswith(k):
                binary, text, fetch = cfg.handlers[handler][k]
                break
        else:
            if None in cfg.handlers[handler]:
                binary, text, fetch = cfg.handlers[handler][None]
            else:
                cfg.log("No default %s handler defined!" % handler)
                return


        # Escape all "s in the URL, to avoid malicious use
        # of crafted feeds. Thanks to Andreas.
        href = href.replace("\"","%22")

        if text:
            cfg.wait_for_pid = silentfork(binary, href, 1, fetch)
        else:
            silentfork(binary, href, 0, fetch)
    else:
        cfg.log("No handler set for %s" % handler)

def stripchars(string):
    string = string.replace("\\","\\\\")
    string = string.replace("%", "\\%")
    return string

def strip_escape_chars(strings):
    return (re.sub("\\\\(.)", "\\1", string) for string in strings)
