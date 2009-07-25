# -*- coding: utf-8 -*-

#Canto - ncurses RSS reader
#   Copyright (C) 2008 Jack Miller <jack@codezen.org>
#
#   This program is free software; you can redistribute it and/or modify
#   it under the terms of the GNU General Public License version 2 as 
#   published by the Free Software Foundation.

# Like canto-fetch, canto-inspect is a standalone binary that's just merged into
# the source because it's convenient. Right now, c-i essentially amounts to a
# custom pretty printer for content from a feed. Eventually, I'd like it to
# share canto's config such that you can ask it to display on-disk data more
# easily, but that can come at a future date.

# Also, I initially intended for this tool to be much smarter. I wanted it to
# compress lists, eliminate more extraneous content, highlight interesting stuff
# in the feeds, but in reality it's too much effort for too little gain, when
# users that want to use this tool generally know what they're looking for. As
# it is, it just provides a nice layout for the feed XML.

# There are a number of important differences between this custom pretty printer
# and the nice dict pretty printer in the pprint module.
#
#   - Truncates strings to 100 characters. In general, strings in feeds that are
#   longer than that (i.e. descriptions) are already displayed and 100
#   characters is enough to get the gist of the content.
#
#   - Removed a lot of unnecessary Python artifacts. For example, strings are
#   printed without u'', dicts without {}, lists without [], etc. The types are
#   already evident.
#
#   - Demarcate list indexes to make it easier to to tell where one item ends
#   and another begins.

# These improvements lend themselves to readability, in my opinion, but if
# anyone cares to do it, it would be dead simple to code a option to use the
# default pprint.

import feedparser
import codecs
import time
import sys

FILE = "/dev/stdout"

def print_usage():
    print "USAGE: canto-inspect URL"

def out(message):
    f = codecs.open(FILE, "a", "UTF-8")
    f.write(message)
    f.close()

def pretty_print(obj, prefix="", indent = 0):
    indentstr = "    " * indent
    if type(obj) in [unicode, str]:
        out(": %s\n" % obj.replace("\n", " ")[:100])
        return
    elif type(obj) in [int, tuple, time.struct_time]:
        out(": %s\n" % obj)
        return
    else:
        out("\n")

    if hasattr(obj, "keys"):
        for k in obj.keys():
            out(indentstr + ("[%s]" % k))
            pretty_print(obj[k], "", indent + 1)
    elif type(obj) == list:
        for x, i in enumerate(obj):
            out(indentstr + ("[%d]" % x))
            pretty_print(i, prefix, indent + 1)

def main():
    if len(sys.argv) != 2:
        print_usage()
        sys.exit(-1)
    else:
        URL = sys.argv[1]

    d = feedparser.parse(URL)
    pretty_print(d)
