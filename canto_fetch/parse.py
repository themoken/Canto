#Canto - ncurses RSS reader
#   Copyright (C) 2008 Jack Miller <jack@codezen.org>
#
#   This program is free software; you can redistribute it and/or modify
#   it under the terms of the GNU General Public License version 2 as 
#   published by the Free Software Foundation.

import xml.parsers.expat
import urllib2
import htmlentitydefs
import re

class ParsedFeed(list):
    def __init__(self, URL, log_func):
        list.__init__(self)
        self.log = log_func
        self.clear()
        self.link_base = ""

        p = xml.parsers.expat.ParserCreate()
        p.StartElementHandler = self.start
        p.EndElementHandler = self.end
        p.CharacterDataHandler = self.strings

        self.log("Parsing.\n")

        try :
            c = urllib2.urlopen(URL).read()
        except:
            self.log("Error fetching feed!\n")
            return
        
        try:
            p.Parse(c, 1)
        except xml.parsers.expat.ExpatError, v:
            self.log("Parser error!\n")
            self.log("LINE: %d\n" % v.lineno)
            self.log("OFFSET: %d\n" % v.offset)
            self.log("CODE: %d\n" % v.code)
    
    def __getentity(self, name):
        """Convert an entity reference into a printable
           Unicode character."""
        name, = name.groups()
        if htmlentitydefs.name2codepoint.has_key(name):
            return unichr(htmlentitydefs.name2codepoint[name])
        else:
            return "&%s;" % (name,)

    def __getchar(self, num):
        num, = num.groups()
        """Convert a character reference into a printable
           Unicode character."""
        try :
            if num[0] in ['x','X']:
                c = int(num[1:], 16)
            else:
                c = int(num)
        except :
            return num
        return unichr(c)

    def entstrip(self, str):
        string = re.sub("&(\w{1,8});", self.__getentity, str)
        string = re.sub("&#([xX]?[0-9a-fA-F]+)[^0-9a-fA-F]", self.__getchar, string)
        return string

    def clear(self):
        self.item = {}
        self.string = ""
        self.tag = ""
        self.atom = 0

    def start(self, name, attrs):
        if name in ["title", "content", "description", "summary"] :
            self.string = ""
            self.tag = name
            return

        if self.tag in ["content", "summary"]:
            self.string += "<" + name
            for a in attrs.keys():
                self.string += " %s=\"%s\"" % (a, attrs[a])
            self.string += ">"
            return

        if name == "feed" and attrs.has_key("xml:base"):
            self.link_base = attrs["xml:base"]
    
        if name == "link" :
            if self.atom :
                if attrs.has_key('rel') and attrs.has_key('href'):
                    if attrs['rel'] == "alternate":
                        self.string = attrs['href']
                else:
                    self.string = ""
            else:
                self.string = ""
            self.tag = name
            return

        if name == "guid":
            if attrs.has_key('isPermaLink') and attrs['isPermaLink'] == "true":
                self.string = ""
                self.tag = name
    
        if name in ["item", "entry"]:
            self.clear()
            if name == "entry":
               self.atom = 1
            return

    def strings(self, data):
        self.string += data

    def end(self, name):
        if self.tag in ["content", "summary"] and name != self.tag:
            self.string += "</%s>" % (name,)
            return

        if name in ["item", "entry"]:
            # Default to summary, instead of description, if 
            # necessary

            if not self.item.has_key("description") and \
                self.item.has_key("summary"):
                self.item["description"] = self.item["summary"]

            # Default link to guid isPermaLink, if no other
            # link specified.

            if not self.item.has_key("link") and \
                self.item.has_key("guid"):
                self.item["link"] = self.item["guid"]
                    
            for k in ["title", "link", "description"]:
                if not self.item.has_key(k):
                    self.item[k] = "None"

            # To avoid malicious items escaping the directory.
            # In addition, keeps items from being "hidden"

            if self.item["title"].startswith("."):
                self.item["title"] = " " + self.item["title"]

            self.item["hash"] = abs((hash(self.item["link"]) / 8) + \
                    (hash(self.item["description"])))

            self.append(self.item)
            self.clear()

        if self.tag == name :
            self.string = self.entstrip(self.string.rstrip().lstrip())
            if not self.string:
                self.string = "None"
            if name in ["title", "description", "summary"]:
                self.item[name] = self.string
            elif name in ["link", "guid"]:
                self.item[name] = self.link_base + self.string
            elif name == "content":
                self.item["description"] = self.string
            self.tag = ""
