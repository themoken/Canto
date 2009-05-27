# -*- coding: utf-8 -*-

#Canto - ncurses RSS reader
#   Copyright (C) 2008 Jack Miller <jack@codezen.org>
#
#   This program is free software; you can redistribute it and/or modify
#   it under the terms of the GNU General Public License version 2 as 
#   published by the Free Software Foundation.

def register(c):
    c.handlers = {
        "link" : {},
        "image" : {}
    }

    def handler(handlers, path, **kwargs):
        if not "text" in kwargs:
            kwargs["text"] = False
        if not "fetch" in kwargs:
            kwargs["fetch"] = False
        if not "ext" in kwargs:
            kwargs["ext"] = None
        handlers.update(\
                {kwargs["ext"] : (path, kwargs["text"], kwargs["fetch"])})

    def image_handler(path, **kwargs):
        handler(c.handlers["image"], path, **kwargs)

    def link_handler(path, **kwargs):
        handler(c.handlers["link"], path, **kwargs)

    c.locals.update({
        "link_handler": link_handler,
        "image_handler": image_handler})

def post_parse(c):
    pass

def validate(c):
    pass

def test(c):
    pass
