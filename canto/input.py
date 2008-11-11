# -*- coding: utf-8 -*-

#Canto - ncurses RSS reader
#   Copyright (C) 2008 Jack Miller <jack@codezen.org>
#
#   This program is free software; you can redistribute it and/or modify
#   it under the terms of the GNU General Public License version 2 as 
#   published by the Free Software Foundation.

import curses

class Input :
    def __init__(self, cfg, prompt, func, register, deregister):
        cfg.msg.addstr("\n" + prompt + ": ")

        curses.echo()
        self.term = cfg.msg.getstr()
        curses.noecho()

        self.func = func
        self.callfunc()

    def callfunc(self):
        self.func(self.term)
        
class Search(Input):
    def callfunc(self):
        if not self.term :
            self.func(None)
            return
        elif self.term.startswith("rgx:"):
            str = self.term[4:]
        else:
            str = ".*" + re.escape(self.term) + ".*"
        
        try:
            m = re.compile(str)
        except:
            self.func(None)

        self.func(m)
