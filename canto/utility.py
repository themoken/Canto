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

def silentfork(path, text):
    """Fork/exec a path with args, ensure it's quiet."""

    pid = os.fork()
    if not pid :
        if not text :
            os.close(sys.stdout.fileno())
        os.close(sys.stderr.fileno())
        os.system(path)
        sys.exit(-1)

    if text :
        s = signal.getsignal(signal.SIGALRM)
        signal.signal(signal.SIGALRM, signal.SIG_IGN)
        while 1:
            try:
                os.waitpid(pid, 0)
            except OSError:
                continue
            break
        signal.signal(signal.SIGALRM, s)

    return pid

def getlinks(string):
    """Convert entities and escaped chars into unicode, grab links"""
    links = re.findall("<a\s+href=\"(.*?)\".*?>(.*?)</\s*a\s*>", string)
    return links 

def stripchars(string):
    """Make strings safe for inclusion in a t_print 
       statement."""
    string = string.replace("\\","\\\\")
    string = string.replace("%", "\\%")
    return string

def strip_escape_chars(strings):
    return (re.sub("\\\\(.)", "\\1", string) for string in strings)
