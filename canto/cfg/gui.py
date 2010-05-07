# -*- coding: utf-8 -*-

#Canto - ncurses RSS reader
#   Copyright (C) 2008 Jack Miller <jack@codezen.org>
#
#   This program is free software; you can redistribute it and/or modify
#   it under the terms of the GNU General Public License version 2 as 
#   published by the Free Software Foundation.

from canto.const import VERSION_TUPLE

def default_status(c):
    return u"%8%B" + u"Canto %d.%d.%d" % VERSION_TUPLE + u"%b%1"

def register(c):
    c.columns = 1
    c.height = 0
    c.width = 0

    c.reader_lines = 0
    c.reader_orientation = None

    c.cursor_type = "middle"

    c.gui_top = 0
    c.gui_right = 0
    c.gui_height = 0
    c.gui_width = 0

    c.status = default_status

    c.locals.update({
        "cursor_type" : c.cursor_type,
        "status" : c.status,
        "reader_orientation" : c.reader_orientation,
        "reader_lines" : c.reader_lines,
        "columns" : c.columns})

def post_parse(c):
    for attr in ["columns", "reader_orientation",
            "reader_lines", "status", "cursor_type"]:
        setattr(c, attr, c.locals[attr])

def validate(c):
    if c.cursor_type not in ["page","old","edge","top","middle","bottom"]:
        raise Exception, """cursor_type must be "page", "old", "edge",""" +\
            """ "top", "middle", or "bottom". Not "%s".""" % c.cursor_type

    if c.reader_orientation not in ["top","bottom","left","right",None]:
        raise Exception, """reader_orientation must be "top", "bottom",""" +\
            """ "left", "right", or None. Not "%s".""" % c.reader_orientation

    if type(c.reader_lines) != int:
        raise Exception, "reader_lines must be an >= 0 integer."

    if c.reader_lines < 0:
        raise Exception, "reader_lines must be >= 0, not %d" % c.reader_lines

    if type(c.columns) != int:
        raise Exception, "columns must be an >= 0 integer."

    if c.columns < 0:
        raise Exception, "columns must be an >= 0 integer, not %d" % \
                c.columns

def test(c):
    pass
