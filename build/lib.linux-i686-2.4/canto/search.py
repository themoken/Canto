# -*- coding: utf-8 -*-

#Canto - ncurses RSS reader
#   Copyright (C) 2007 Jack Miller <jjm2n4@umr.edu>
#
#   This program is free software; you can redistribute it and/or modify
#   it under the terms of the GNU General Public License version 2 as 
#   published by the Free Software Foundation.

import re
import input

class Search(input.Input):
    """Search sub-classes Input, but instead of returning a 
    simple string it returns a compiled regex to match against."""

    def __init__(self, cfg, caption, func, height, width, log):
        input.Input.__init__(self, cfg, caption, func, height, width, log)
        
    def destroy(self):
        self.cfg.pop_handler()

    def callfunc(self):
        if not self.term :
            self.func(None)
            return
        elif self.term.startswith("rgx:"):
            str = self.term[4:]
        else :
            str = ".*" + re.escape(self.term) + ".*"
        
        try:
            m = re.compile(str)
        except :
            self.func(None)

        self.func(m)
