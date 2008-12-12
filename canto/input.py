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

# I am aware that Python's curses library comes with a TextBox class
# and, indeed, the input() function was using it for awhile. The problems
# with Textbox were numerous though:
#   * Only ASCII characters could be printed/inputted (the *big* one)
#   * Included a whole bunch of multi-line editing and validation stuff
#       that was completely unnecessary, since we know the input line
#       only needs to be one line long.
#   * To make editing easier, it used a half-ass system of gathering
#       the data from the window's written content with win.inch(),
#       which apparently didn't play nice with multi-byte?
#
# All of these problems have been fixed in half as many lines with all
# the same functionality on a single line basis, but the design is still
# based on Textbox.

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
        try:
            self.win.addstr(self.result[-1 * (maxx - self.minx):]\
                    .encode("UTF-8", "replace"))
        except:
            pass
        self.win.clrtoeol()
        self.win.move(0, min(self.x, maxx - 1))
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
        elif ch in (ascii.ACK, curses.KEY_RIGHT): # C-f
            self.x += 1
            if len(self.result) + self.minx < self.x:
                self.result += " "
        elif ch in (ascii.ENQ, curses.KEY_END): # C-e
            self.x = self.minx + len(self.result)
        elif ch in (ascii.SOH, curses.KEY_HOME): # C-a
            self.x = self.minx
        elif ch == ascii.NL: # C-j
            return 0
        elif ch == ascii.BEL: # C-g
            return -1
        elif ch == ascii.FF: # C-l
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
 
    curses.curs_set(1)
    term = InputBox(cfg.msg).edit()
    curses.curs_set(0)

    signal.signal(signal.SIGALRM, temp)
    signal.alarm(1)

    cfg.msg.erase()
    cfg.msg.refresh()

    return term

def num_input(cfg, prompt):
    term = input(cfg, prompt)
    if not term:
        return

    try:
        term = int(term)
    except:
        cfg.log("Not a number.")
        return None

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
