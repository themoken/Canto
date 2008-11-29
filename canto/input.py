# -*- coding: utf-8 -*-

#Canto - ncurses RSS reader
#   Copyright (C) 2008 Jack Miller <jack@codezen.org>
#
#   This program is free software; you can redistribute it and/or modify
#   it under the terms of the GNU General Public License version 2 as 
#   published by the Free Software Foundation.

from curses import ascii
import curses
import signal
import re

class InputBox:
    def __init__(self, win):
        self.minx = win.getyx()[1]
        self.x = self.minx

        self.win = win
        self.win.keypad(1)
        self.result = ""

    def refresh(self):
        self.win.move(0, self.minx)
        maxx = self.win.getmaxyx()[1]
        maxx -= self.minx
        self.win.addstr(self.result[-maxx:].encode("UTF-8", "replace"))
        self.win.clrtoeol()
        self.win.move(0, self.x)
        self.win.refresh()

    def key(self, ch):
        if ch in (ascii.STX, curses.KEY_LEFT):
            if self.x > self.minx:
                self.x -= 1
        elif ch in (ascii.BS, curses.KEY_BACKSPACE):
            if self.x > self.minx:
                idx = self.x - self.minx
                self.result = self.result[:idx - 1] + self.result[idx:]
                self.x -= 1
        elif ch in (ascii.ACK, curses.KEY_RIGHT):
            self.x += 1
            if len(self.result) + self.minx < self.x:
                self.result += " "
        elif ch in (ascii.ENQ, curses.KEY_END):
            self.x = self.minx + len(self.result)
        elif ch in (ascii.SOH, curses.KEY_HOME):
            self.x = self.minx
        elif ch == ascii.NL:
            return 0
        elif ch == ascii.BEL:
            return -1
        elif ch == ascii.FF:
            self.refresh()
        else:
            self.x += 1
            idx = self.x - self.minx
            self.result = self.result[:idx] + unichr(ch) + self.result[idx:]
        return 1

    def edit(self):
        while 1:
            ch = self.win.getch()
            if ch <= 0:
                continue
            r = self.key(ch)
            if not r:
                break
            if r < 0:
                self.result = None
                break
            self.refresh()
        return self.result

def input(cfg, prompt):
    cfg.message("%B%1" + prompt + ":%b ")

    cfg.msg.move(0, len(prompt) + 2)

    temp = signal.getsignal(signal.SIGALRM)
    signal.signal(signal.SIGALRM, signal.SIG_IGN)
    
    term = InputBox(cfg.msg).edit()

    signal.signal(signal.SIGALRM, temp)
    signal.alarm(1)

    cfg.msg.erase()
    cfg.msg.refresh()

    return term

def search(cfg, prompt):
    term = input(cfg, prompt)
    if not term :
        return

    elif term.startswith("rgx:"):
        str = term[4:]
    else:
        str = ".*" + re.escape(term) + ".*"
    
    try:
        m = re.compile(str)
    except:
        return None

    return m
