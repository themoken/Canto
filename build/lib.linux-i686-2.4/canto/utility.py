# -*- coding: utf-8 -*-

#Canto - ncurses RSS reader
#   Copyright (C) 2007 Jack Miller <jjm2n4@umr.edu>
#
#   This program is free software; you can redistribute it and/or modify
#   it under the terms of the GNU General Public License version 2 as 
#   published by the Free Software Foundation.

import re
import sys
import os
import signal 

def qasplit(path):
    """Quote aware split."""
    args = []
    arg = ""
    quote = 0

    for c in path :
        if c == " " and quote == 0:
            args.append(arg)
            arg = ""
        elif c == "\"" :
            quote = not quote
        else:
            arg += c

    if arg :
        args.append(arg)

    return args

def silentfork(path, text):
    """Fork/exec a path with args, ensure it's quiet."""

    args = qasplit(path)        
    os.setpgid(os.getpid(), os.getpid())
    pid = os.fork()
    if not pid :
        if not text :
            os.close(sys.stdout.fileno())
        os.close(sys.stderr.fileno())
        os.setpgid(os.getpid(), os.getpid())
        os.execve(args[0], args, os.environ)
        sys.exit(-1)
    if text :
        s = signal.getsignal(signal.SIGALRM)
        signal.signal(signal.SIGALRM, signal.SIG_IGN)
        os.tcsetpgrp(sys.stdin.fileno(), pid)
        os.waitpid(pid, 0)
        os.tcsetpgrp(sys.stdin.fileno(), os.getpid())
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
