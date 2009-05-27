# -*- coding: utf-8 -*-

#Canto - ncurses RSS reader
#   Copyright (C) 2008 Jack Miller <jack@codezen.org>
#
#   This program is free software; you can redistribute it and/or modify
#   it under the terms of the GNU General Public License version 2 as 
#   published by the Free Software Foundation.

def register(c):
    c.triggers = ["interval","signal"]
    c.locals.update({"triggers" : c.triggers})

def post_parse(c):
    c.triggers = c.locals["triggers"]

def validate(c):
    if type(c.triggers) != list:
        raise Exception, "triggers must be a list (%s)" % c.triggers
    for t in c.triggers:
        if t not in ["interval","signal","change_tag"]:
            raise Exception, "%s is not a valid trigger name, try\
                    \"interval\", \"signal\", or \"change_tag\"" % t

def test(c):
    pass
