# -*- coding: utf-8 -*-

#Canto - ncurses RSS reader
#   Copyright (C) 2008 Jack Miller <jack@codezen.org>
#
#   This program is free software; you can redistribute it and/or modify
#   it under the terms of the GNU General Public License version 2 as 
#   published by the Free Software Foundation.

from canto.feed import Feed

def register(c):
    c.feeds = []
    c.default_rate = 5
    c.default_keep = 40
    c.never_discard = []

    def add(URL, **kwargs):
        if (not URL) or URL == "" or type(URL) not in [unicode, str]:
            raise Exception, "%s is not a valid URL" % URL

        for key in ["keep","rate"]:
            if not key in kwargs:
                kwargs[key] = getattr(c, "default_" + key)
            elif type(kwargs[key]) != int:
                raise Exception, "%s's %s must be an integer." % (URL, key)

        for key in ["username","password"]:
            if not key in kwargs:
                kwargs[key] = None
            elif type(kwargs[key]) not in [unicode, str]:
                raise Exception, "%s's %s must be a string." % (URL, key)

        if "filter" not in kwargs:
            kwargs["filter"] = None

        if not "tags" in kwargs:
            kwargs["tags"] = [None]
        else:
            tgs = []
            for tag in kwargs["tags"]:
                if tag:
                    if type(tag) not in [unicode,str]:
                        raise Exception, "%s's tags must be strings." % URL
                    elif type(tag) == str:
                        tgs.append(unicode(tag, "UTF-8", "ignore"))
                    else:
                        tgs.append(tag)
                else:
                    tgs.append(None)
            kwargs["tags"] = tgs

        # The tag is the only thing that has to be unique, so we ignore
        # any duplicate URLs, or everything  will break.

        if not URL in [f.URL for f in c.feeds]:
            c.feeds.append(Feed(c, c.feed_dir +\
                    URL.replace("/", " "), URL,
                    kwargs["tags"],
                    kwargs["rate"],
                    kwargs["keep"],
                    kwargs["filter"],
                    kwargs["username"],
                    kwargs["password"]))
        return True

    def change_feed(URL, **kwargs):
        for f in c.feeds:
            if f.URL == URL:
                c.feeds.remove(f)
                add(URL, **kwargs)
                break

    def set_default_rate(rate):
        c.default_rate = rate

    def set_default_keep(keep):
        c.default_keep = keep

    def never_discard(tag):
        c.never_discard.append(tag)

    c.locals.update({
        "add" : add,
        "change_feed" : change_feed,
        "default_rate" : set_default_rate,
        "default_keep" : set_default_keep,
        "never_discard" : never_discard})

def post_parse(c):
    pass

# Fortunately, we can be pretty lax about validating feeds. The config functions
# guarantee that we won't have feeds with the same URL and that the types are
# all in order. It's important that that's done right off the bat because
# between post_parse and validate the feed information will be used.

def validate(c):
    pass

def test(c):
    add = c.locals["add"]
    add("http://someurl")
    if c.feeds[0].rate != c.default_rate:
        raise Exception, "Default rate not transferring"
    if c.feeds[0].keep != c.default_keep:
        raise Exception, "Default keep not transferring"

    add("http://someurl")
    if len(c.feeds) > 1:
        raise Exception, "Duplicate URL allowed."

    c.locals["default_rate"](777)
    c.locals["default_keep"](777)
    add("http://someotherurl")
    if c.feeds[1].rate != 777:
        raise Exception, "Set default rate not transferred"
    if c.feeds[1].keep != 777:
        raise Exception, "Set default keep not transferred"

    c.feeds = []
    try:
        add(None)
    except:
        pass
    else:
        raise Exception, "Invalid URL didn't raise exception."

    try:
        add("blah", rate="bad")
    except:
        pass
    else:
        raise Exception, "Invalid rate didn't raise exception."

    try:
        add("blah", keep="bad")
    except:
        pass
    else:
        raise Exception, "Invalid keep didn't raise exception"

    try:
        add("blah", username=0xdeadbeef)
    except:
        pass
    else:
        raise Exception, "Invalid username didn't raise exception"

    try:
        add("blah", password=0xdeadcafe)
    except:
        pass
    else:
        raise Exception, "Invalid password didn't raise exception"
    print "Feed tests passed"
