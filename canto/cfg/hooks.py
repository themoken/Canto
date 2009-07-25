# -*- coding: utf-8 -*-

#Canto - ncurses RSS reader
#   Copyright (C) 2008 Jack Miller <jack@codezen.org>
#
#   This program is free software; you can redistribute it and/or modify
#   it under the terms of the GNU General Public License version 2 as 
#   published by the Free Software Foundation.

import traceback

def hook_dec(c, fn):
    if not fn:
        return None

    def hdec(*args):
        try:
            r = fn(*args)
        except:
            c.log("\nException in hook:")
            c.log("%s" % traceback.format_exc())
            return 0
        return r
    return hdec

hooks = ["resize_hook","new_hook","select_hook","update_hook",\
            "unselect_hook","start_hook","end_hook", "state_change_hook"]
def register(c):
    for h in hooks:
        setattr(c, h, None)
        c.locals.update({ h : getattr(c, h)})

def post_parse(c):
    for h in hooks:
        setattr(c, h, c.locals[h])

def validate(c):
    for h in hooks:
        hk = getattr(c, h)
        if not hk:
            continue
        if not hasattr(hk, "__call__"):
            raise "All hooks must be callable. (%s)" % hk
        setattr(c, h, hook_dec(c, hk))

def test(c):
    pass
