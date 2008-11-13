#!/usr/bin/python

#Canto - ncurses RSS reader
#   Copyright (C) 2008 Jack Miller <jack@codezen.org>
#
#   This program is free software; you can redistribute it and/or modify
#   it under the terms of the GNU General Public License version 2 as 
#   published by the Free Software Foundation.

#   This was inspired by Aaron Swartz's html2text, but doesn't do
#   file IO, doesn't do markdown, and doesn't shy away from Unicode.

import htmlentitydefs
import sgmllib
import re

sgmllib.charref = re.compile('&#([xX]?[0-9a-fA-F]+)[^0-9a-fA-F]')

class CantoHTML(sgmllib.SGMLParser):

    # Reset is used, instead of __init__ so a single
    # instance of the class can parse multiple HTML
    # fragments.

    def reset(self):
        sgmllib.SGMLParser.reset(self)
        self.result = ""
        self.link_count = 0
        self.link_decoration = 1
        self.list_stack = []
        self.verbatim = 0

    # unknown_* funnel all tags to handle_tag

    def unknown_starttag(self, tag, attrs):
        self.handle_tag(tag, attrs, 1)

    def unknown_endtag(self, tag):
        self.handle_tag(tag, {}, 0)

    def handle_data(self, text):
        if self.verbatim > 0:
            self.result += text
        else:
            self.result += text.replace("\n", " ")

    # convert_* are called by SGMLParser's default
    # handle_char/entityref functions.

    def convert_charref(self, ref):
        try:
            if ref[0] in ['x','X']:
                c = int(ref[1:], 16)
            else:
                c = int(ref)
        except:
            return "[?]"
        return unichr(c)

    def convert_entityref(self, ref):
        if htmlentitydefs.name2codepoint.has_key(ref):
            return unichr(htmlentitydefs.name2codepoint[ref])
        return "[?]"

    # This is the real workhorse of the HTML parser.

    def handle_tag(self, tag, attrs, open):
        if tag in ["h" + str(x) for x in xrange(1,7)]:
            if open:
                self.result += "\n%B"
            else:
                self.result += "%b\n"
        if tag in ["blockquote"]:
            if open:
                self.result += "\n%Q"
            else:
                self.result += "%q\n"
        elif tag in ["pre","code"]:
            if open:
                if tag == "pre":
                    self.result += "\n%Q"
                self.verbatim += 1
            else:
                if tag == "pre":
                    self.result += "%q\n"
                self.verbatim -= 1
        elif tag in ["sup"]:
            if open:
                self.result += "^"
        elif tag in ["p", "br", "div"]:
            self.result += "\n"
        elif tag in ["ul", "ol"]:
            if open:
                self.result += "\n%I"
                self.list_stack.append([tag,0])
            else:
                self.list_stack.pop()
                self.result += "%i\n"
        elif tag in ["li"]:
            if open:
                self.result += "\n"
                if self.list_stack[-1][0] == "ul":
                    self.result += u"\u25CF "
                else:
                    self.list_stack[-1][1] += 1
                    self.result += str(self.list_stack[-1][1])+ "."
        elif tag in ["a"]:
            if open:
                self.result += "%4"
                self.link_count += 1
            else:
                if self.link_decoration:
                    self.result += "[" + str(self.link_count) + "]"
                self.result += "%1"
        elif tag in ["img"]:
            if open:
                self.result += "[image]"
        elif tag in ["i", "small", "em"]:
            if open:
                self.result += "%6%B"
            else:
                self.result += "%b%1"
        elif tag in ["b", "strong"]:
            if open:
                self.result += "%B"
            else:
                self.result += "%b"

instance = CantoHTML()
def ent_wrapper(match):
    return CantoHTML.convert_entityref(instance,\
         match.groups()[0]).encode("UTF-8")

def char_wrapper(match):
    return CantoHTML.convert_charref(instance,\
        match.groups()[0]).encode("UTF-8")

def convert(s):
    instance.feed(unicode(s,"UTF-8"))
    r = instance.result
    instance.reset()
    return r.encode("UTF-8")

if __name__ == "__main__":
    print "Testing canto_html"
    print "1. Proper list nesting"

    print convert("<ul><li>Unordered</li><li>Some header text\
            <ol><li>Ordered</li><li>Also ordered</li></ol>\
            <li>Unordered, too</li></ul>")
