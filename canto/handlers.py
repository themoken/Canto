#Canto - ncurses RSS reader
#   Copyright (C) 2008 Jack Miller <jack@codezen.org>
#
#   This program is free software; you can redistribute it and/or modify
#   it under the terms of the GNU General Public License version 2 as 
#   published by the Free Software Foundation.

class Handler():
    def __init__(self):
        self.reset()

    def get_attr(self, attrs, attr):
        l = [v for k,v in attrs if k == attr]
        if l :
            return l[0]

class LinkHandler(Handler):
    def reset(self):
        self.active = 0
        self.link = ""
        self.content = ""
        self.handler = "link"

    def match(self, tag, attrs, open, ll):
        if tag == "a":
            if open:
                href = self.get_attr(attrs, "href")
                if href:
                    self.link = href
                    self.active = 1
                    return "%4"
                else:
                    self.reset()
            else:
                ll.append((self.content, self.link, self.handler))
                self.reset()
                return u"[" + unicode(len(ll)) + u"]%0"

class ImageHandler(Handler):
    def reset(self):
        self.active = 0
        self.handler = "image"

    def match(self, tag, attrs, open, ll):
        if tag == "img":
            if open:
                src = self.get_attr(attrs, "src")
                alt = self.get_attr(attrs, "alt")
                if not alt:
                    alt = "image"
                if src:
                    extension = src.rsplit('.',1)[-1]
                    ll.append((alt, src, self.handler))
                self.reset()
                return u"%7["+ alt + u"][" + unicode(len(ll)) + u"]%0"
