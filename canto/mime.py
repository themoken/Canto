#Canto - ncurses RSS reader
#   Copyright (C) 2008 Jack Miller <jack@codezen.org>
#
#   This program is free software; you can redistribute it and/or modify
#   it under the terms of the GNU General Public License version 2 as 
#   published by the Free Software Foundation.

class Handler():
    def __init__(self, ll):
        self.ll = ll
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
        self.handler = "browser"

    def match(self, tag, attrs, open):
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
                self.ll.append((self.content.encode("UTF-8"),\
                        self.link.encode("UTF-8"),\
                        self.handler.encode("UTF-8")))
                self.reset()
                return "[" + str(len(self.ll)) + "]%1"

class ImageHandler(Handler):
    def reset(self):
        self.active = 0
        self.handler = "image"

    def match(self, tag, attrs, open):
        if tag == "img":
            if open:
                src = self.get_attr(attrs, "src")
                alt = self.get_attr(attrs, "alt")
                if not alt:
                    alt = "image"
                if src:
                    self.ll.append((alt.encode("UTF-8"),\
                        src.encode("UTF-8"),\
                        self.handler.encode("UTF-8")))
                self.reset()
                return "%7["+ alt +"][" + str(len(self.ll)) + "]%0"
