# -*- coding: utf-8 -*-

#Canto - ncurses RSS reader
#   Copyright (C) 2008 Jack Miller <jack@codezen.org>
#
#   This program is free software; you can redistribute it and/or modify
#   it under the terms of the GNU General Public License version 2 as 
#   published by the Free Software Foundation.

from const import *

class BaseGui:
    def key(self, k):
        if k in self.keys:
            if type(self.keys[k]) == list:
                return self.keys[k]
            return [self.keys[k]]
        else:
            return []

    def action(self, a):
        if hasattr(a, "__call__"):
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
