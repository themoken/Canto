# -*- coding: utf-8 -*-

#Canto - ncurses RSS reader
#   Copyright (C) 2008 Jack Miller <jack@codezen.org>
#
#   This program is free software; you can redistribute it and/or modify
#   it under the terms of the GNU General Public License version 2 as 
#   published by the Free Software Foundation.

import re
import sys
import os
import signal 
import curses

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
        if colordir.has_key(c):
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

def silentfork(path, text):

    pid = os.fork()
    if not pid :
        if not text :
            os.close(sys.stdout.fileno())
        os.close(sys.stderr.fileno())
        os.system(path)
        sys.exit(-1)

    if text:
        signal.signal(signal.SIGALRM, signal.SIG_IGN)

    return pid

def goto(URL, cfg):
    URL = URL.replace("\"","%22")
    s = re.sub("%u", URL, cfg.browser)
    if cfg.text_browser:
        cfg.wait_for_pid = silentfork(s, 1)
    else:
        silentfork(s, 0)

def getlinks(string):
    s = re.sub("\\\n", " ", string[:])
    links = re.findall("<a[^>]+?href=\"(.*?)\".*?>(.*?)</\s*a\s*>", s)
    return links 

def stripchars(string):
    string = string.replace("\\","\\\\")
    string = string.replace("%", "\\%")
    return string

def strip_escape_chars(strings):
    return (re.sub("\\\\(.)", "\\1", string) for string in strings)
