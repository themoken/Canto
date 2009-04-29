# -*- coding: utf-8 -*-

#Canto - ncurses RSS reader
#   Copyright (C) 2008 Jack Miller <jack@codezen.org>
#
#   This program is free software; you can redistribute it and/or modify
#   it under the terms of the GNU General Public License version 2 as 
#   published by the Free Software Foundation.

from const import *

class BaseGui:
    def action(self, k):
        if k in self.keys:
            a = self.keys[k]
        elif type(k) == str:
            a = k
        else:
            return NOKEY

        if type(a) == list:
            for action in a:
                return self.action(action)
        elif hasattr(a, "__call__"):
            r = a(self)
        else:
            f = getattr(self, a, None)
            if f:
                r = f()
            else:
                r = NOKEY

        if not r:
            self.draw_elements()
        return r
