# -*- coding: utf-8 -*-

#Canto - ncurses RSS reader
#   Copyright (C) 2008 Jack Miller <jack@codezen.org>
#
#   This program is free software; you can redistribute it and/or modify
#   it under the terms of the GNU General Public License version 2 as 
#   published by the Free Software Foundation.

# BaseGui enforces that all gui objects have the same basic interface. For
# BaseGui ever single function is at least partially overridden, but the Reader
# class can take most of it at default value.

from const import NOKEY

class BaseGui:
    def __init__(self):
        self.keys = {}
    
    def draw_elements():
        pass

    # Translate a key into a set of actions based on self.keys
    def key(self, k):
        if k in self.keys:
            if type(self.keys[k]) == list:
                return self.keys[k]
            return [self.keys[k]]
        else:
            return []

    # Perform the action. If it's a string, attempt to look it up as an
    # attribute of the self object. If it's a callable, go ahead and call it.

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
