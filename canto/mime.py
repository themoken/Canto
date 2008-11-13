#Canto - ncurses RSS reader
#   Copyright (C) 2008 Jack Miller <jack@codezen.org>
#
#   This program is free software; you can redistribute it and/or modify
#   it under the terms of the GNU General Public License version 2 as 
#   published by the Free Software Foundation.

class LinkHandler():
    def __init__(self, ll):
        self.ll = ll
        self.reset()

    def reset(self):
        self.active = 0
        self.link = ""
        self.content = ""
        self.handler = "browser"

    def match(self, tag, attrs, open):
        if tag == "a":
            if open:
                href = [v for k,v in attrs if k == "href"]
                if href:
                    self.link = href[0]
                    self.active = 1
                else:
                    self.reset()
            else:
                self.ll.append((self.content.encode("UTF-8"),\
                        self.link.encode("UTF-8"),\
                        self.handler.encode("UTF-8")))
                self.reset()
