#!/usr/bin/python
# -*- coding: utf-8 -*-

#Canto - ncurses RSS reader
#   Copyright (C) 2008 Jack Miller <jack@codezen.org>
#
#   This program is free software; you can redistribute it and/or modify
#   it under the terms of the GNU General Public License version 2 as 
#   published by the Free Software Foundation.

import xml.parsers.expat

def register(c):
    def source(fn):
        def source_dec(*args, **kwargs):
            append = False
            if "append" in kwargs:
                append = kwargs["append"]
                file = codecs.open(c.path, "a", "UTF-8")

            l = fn(*args, **kwargs)

            for f in l:
                if c.locals["add"](f[0], tags=[f[1]]) and append:
                    if f[1]:
                        file.write(u"""add("%s", tags=["%s"])\n""" % f)
                    else:
                        file.write(u"""add("%s")\n""" % f[0])

            if append:
                file.close()
        return source_dec

    @source
    def source_opml(filename, **kwargs):
        l = []
        def start(name, attrs) :
            if name == "outline" and (\
                (("type" in attrs and\
                attrs["type"] in ["pie","rss"])) or\
                not ("type" in attrs)):

                if "xmlUrl" in attrs:
                    if "text" in attrs:
                        l.append((attrs["xmlUrl"], attrs["text"]))
                    else:
                        l.append((attrs["xmlUrl"], None))

        p = xml.parsers.expat.ParserCreate()
        p.StartElementHandler = start
        d = c.read_decode(filename)
        p.Parse(d.encode("UTF-8"), 1)
        return l

    @source
    def source_urls(filename, **kwargs):
        l = []
        d = c.read_decode(filename).split('\n')[:-1]
        for feed in d:
            l.append((feed, None))
        return l

    @source
    def source_url(URL, **kwargs):
        if "tag" in kwargs:
            return [(URL, kwargs["tag"])]
        return [(None, URL)]

    c.locals.update({
          "source_urls" : source_urls,
          "source_url" : source_url,
          "source_opml" : source_opml })

def post_parse(c):
    pass

def validate(c):
    pass

def test(c):
    pass
