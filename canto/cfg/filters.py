# -*- coding: utf-8 -*-

#Canto - ncurses RSS reader
#   Copyright (C) 2008 Jack Miller <jack@codezen.org>
#
#   This program is free software; you can redistribute it and/or modify
#   it under the terms of the GNU General Public License version 2 as 
#   published by the Free Software Foundation.

from canto.utility import Cycle
import types

all_filters = []

class Filter:
    def __str__(self):
        return "Unnamed Filter."

    def __call__(self, tag, item):
        return 1

def filter_dec(c, f):
    if not f:
        return None

    class fdec():
        def __init__(self, instance, log):
            self.instance = instance
            self.log = log

        def __eq__(self, other):
            if not other:
                return False
            return str(self) == str(other)

        def __str__(self):
            return self.instance.__str__()

        def __call__(self, *args):
            try:
                return self.instance(*args)
            except:
                self.log("\nException in filter:")
                self.log("%s" % traceback.format_exc())
    return fdec(f, c.log)

def register(c):
    def set_default_tag_filters(filters):
        c.tag_filters = filters
    c.tag_filters = [None]
    c.filters = [None]
    c.all_filters = []

    c.locals.update({
        "Filter" : Filter,
        "default_tag_filters" : set_default_tag_filters,
        "tag_filters" : c.tag_filters,
        "filters" : c.filters })

def post_parse(c):

    # This has to be done before the validate stage
    # because it has to be done before the update

    # Note that tag_filters isn't moved in because at this point, the tags have
    # all had their filters set explicitly.

    c.all_filters = all_filters
    c.filters = c.locals["filters"]

    for feed in c.feeds:
        if not feed.filter:
            continue
        newfilt = validate_filter(c, feed.filter)
        feed.filter = lambda x : newfilt(feed, x)

def validate_filter(c, f):
    if not f:
        return None
    if type(f) not in [types.ClassType, types.InstanceType]:
        raise Exception, \
            "All filters must be classes that subclass Filter (%s)" % f
    if not isinstance(f, Filter):
        f = f()
    if not issubclass(f.__class__, Filter):
        raise Exception, "All filters must subclass Filter class ("\
                + f.__class__.__name__ + ")"
    return filter_dec(c, f)

def validate(c):
    c.all_filters = [ validate_filter(c, f) for f in c.all_filters ]
    if type(c.filters) != list:
        raise Exception, "filters must be a list %s" % c.filters
    c.filters = [ validate_filter(c, f) for f in c.filters ]
    for filt in c.filters:
        if filt not in c.all_filters:
            c.all_filters.append(filt)
    c.filters = Cycle(c.filters)

    for tag in c.cfgtags:
        if type(tag.filters) != list:
            raise Exception, "tag filters must be a list %s" % tag.filters
        tag.filters = [validate_filter(c, f) for f in tag.filters]
        for filt in tag.filters:
            if filt not in c.all_filters:
                c.all_filters.append(filt)
        tag.filters = Cycle(tag.filters)

def test(c):
    pass
