# -*- coding: utf-8 -*-

#Canto - ncurses RSS reader
#   Copyright (C) 2007 Jack Miller <jack@codezen.org>
#
#   This program is free software; you can redistribute it and/or modify
#   it under the terms of the GNU General Public License version 2 as 
#   published by the Free Software Foundation.

import sys
import utility
import struct
import re
import codecs

class Story(dict):
    """Story() handles a single story. It parses the story
    file into a dictionary, modifies that story file to
    reflect read/unread status and performs the printing
    for a single story."""

    def __init__(self, story_path):
        dict.__init__(self)
        self["name"] = story_path
        self.idx = 0
        self.last = 0

    def __parse(self, item):
        try:
            fsock = codecs.open(item, "r", "UTF-8", "ignore")
            try:
                data = fsock.read().split("\00")[:-1]
            finally:
                fsock.close()

            self["tags"] = data.pop().split(',')
            for tag in ["descr", "link", "title"]:
                self[tag] = utility.stripchars(data.pop())

        except IOError:
            pass

    def __update(self):
        try:
            fsock = open(self["name"], "r+")
            try:
                fsock.seek(fsock.read().rfind("\00", 0, -1) + 1)
                fsock.write(','.join(filter(lambda x : x not in ["selected", "marked"], self["tags"])) + "\00")
                fsock.truncate()
            finally:
                fsock.close()
        except IOError:
            pass

    def __setitem__(self, key, item):
        if key == "name" and item:
            self.__parse(item)
        dict.__setitem__(self, key, item)

    def __eq__(self, other):
        if self["title"] != other["title"]:
            return 0
        if self["link"] != other["link"]:
            return 0
        if self["descr"] != other["descr"]:
            return 0
        return 1

    def __tagwrap(self, tag, i):
        if i == 0:
            return tag in self["tags"]
        elif i == 1 and not tag in self["tags"]:
            self["tags"].append(tag)
        elif i == -1 and tag in self["tags"]:
            self["tags"].remove(tag)
        if tag not in ["marked", "selected"]:
            self.__update()

    def wasread(self):
        return self.__tagwrap("read", 0)

    def read(self):
        self.__tagwrap("read", 1)

    def unread(self):
        self.__tagwrap("read", -1)

    def marked(self):
        return self.__tagwrap("marked", 0)

    def mark(self):
        self.__tagwrap("marked", 1)

    def unmark(self):
        self.__tagwrap("marked", -1)

    def selected(self):
        return self.__tagwrap("selected", 0)

    def select(self):
        self.__tagwrap("selected", 1)

    def unselect(self):
        self.__tagwrap("selected", -1)

    def print_item(self, tag, row, i):
        return i.cfg.render.story(tag, self, row, i.height, i.width / i.cfg.columns, i.window_list)
