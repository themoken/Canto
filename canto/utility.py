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

def daemonize():
    pid = os.fork()
    if not pid:
        os.setsid()
        os.chdir("/")
        os.umask(0)
        pid = os.fork()
        if pid:
            sys.exit(0)
    else:
        sys.exit(0)

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
        if 0 <= c <= 7:
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
        fd = os.open("/dev/null", os.O_RDWR)
        os.dup2(fd, sys.stderr.fileno())

        if not text:
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

    return pid

def goto(link, cfg):
    title,href,handler = link
    if handler in cfg.handlers:
        for k in [h for h in cfg.handlers[handler].keys() if h]:
            if href.endswith(k):
                binary, text, fetch = cfg.handlers[handler][k]
                break
        else:
            binary, text, fetch = cfg.handlers[handler][None]
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
