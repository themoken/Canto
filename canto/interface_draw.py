# -*- coding: utf-8 -*-
from widecurse import core, tlen
import re

class Renderer :
    def __init__(self):
        self.reader_rgx = [(re.compile("<a\s+href=\".*?\".*?>(.*?)</\s*a\s*>"), "%4\\1%1"),
            (re.compile("[\\\"](.*?)[\\\"]"), "%5\\1%1"),
            (re.compile("<p>"), "\n\n"),
            (re.compile("<br\s*/?>"), "\n"),
            (re.compile("<.*?>"), ""),
            (re.compile("[\\\n]{3,}"), "\n\n")]

    def tag_head(self, tag, width):
        t = "%1" + tag.tag.encode("UTF-8") + " [%2" + str(tag.unread) + "%0]"
        if tag.collapsed:
            if tag[0].selected():
                return "%B > " + t + "%C\n\n"
            else:
                return "%B   " + t + "%C\n\n"
        
        s = u"─" * (width - 2)
        return "%B   " + t + u"\n┌" + s + u"┐%C"

    def tag_foot(self, tag, width):
        s = u"─" * (width - 2)
        return u"%B└" + s + u"┘%C\n"

    def firsts(self, story, width):
        base = "%C%1%B│%b "
    
        if story.selected() :
            base += "%B>%b "
        else:
            base += "  "

        if story.marked():
            base += "%1%B"
        else:
            if story.wasread():
                base += "%3"
            else:
                base += "%2%B"

        return (base, 4, " ", 1, " %1%B│%b", 2)

    def mids(self, story, width):
        return ("%B│%b%0      ",7, " ", 1, " %1%B│%b", 2)

    def ends(self, story, width):
        return ("%B│%b%0      ",7, " ", 1, " %1%B│%b", 2)

    def reader_head(self, story, width):
        s = u"─" * (width - 2)
        return u"%1%B" + story["title"] + u"\n┌" + s + u"┐%C\n"

    def reader_foot(self, story, width):
        s = u"─" * (width - 2)
        return u"%B└" + s + u"┘%C\n"

    def reader_link(self, idx, link):
        return "%4[" + str(idx) + "] " + link[1] + "- %1" + link[0]

    def rfirsts(self, story, width):
        return ("%B│%b%1 ", 2, " ", 1, " %1%B│%b", 2)

    def rmids(self, story, width):
        return ("%B│%b%0 ", 2, " ", 1, " %1%B│%b", 2)
    
    def rends(self, story, width):
        return ("%B│%b%0 ", 2, " ", 1, " %1%B│%b", 2)

    def __window(self, row, height, window_list):
        if height != -1:
            winidx, winrow = divmod(row, height)
            if winidx >= len(window_list):
                window = None
            else:
                window = window_list[winidx]
            return (window, winrow)
        else:
            return (window_list[0], row)

    def simple_out(self, s, row, height, width, window_list):
        s = s.encode("UTF-8")
        while s:
            window, winrow = self.__window(row, height, window_list)
            s,x = core(window, winrow, 0, width, 0, s)
            row += 1
        return row

    def out(self, s, first, mid, last, row, height, width, window_list):
        s = s.encode("UTF-8")
        x = 0
        line = 0
        while s :
            window, winrow = self.__window(row + line, height, window_list)

            if line == 0:
                start, slen, rep, rlen, end, elen = first
            else:
                start, slen, rep, rlen, end, elen = mid

            if tlen(s) <= width - (slen + elen):
                if tlen(s) <= width - (last[1] + last[3]):
                    if line == 0:
                        rep, rlen, end, elen = last[2:]
                    else:
                        start, slen, rep, rlen, end, elen = last
                else:
                    s += '\n'

            x = core(window, winrow,x, slen, 0, start)[1]
            s,x = core(window, winrow,x, width - elen - slen - 1, 1, s)
            while x <= width - elen:
                x = core(window, winrow, x, rlen, 0, rep)[1]
            x = core(window, winrow, x - 1, elen, 0, end)[1]
        
            line += 1
            x = 0
        return row + line


    def story(self, tag, story, row, height, width, window_list):
        if story.idx == 0:
            row = self.simple_out(self.tag_head(tag, width),\
                row, height, width, window_list)

        if not tag.collapsed:
            row = self.out(story["title"], 
                    self.firsts(story, width), self.mids(story, width),\
                    self.ends(story, width), row, height, width, window_list)
            
            if story.last:
                row = self.simple_out(self.tag_foot(tag, width),\
                    row, height, width, window_list)
    
        return row

    def reader(self, story, width, links, show_links, window):
        s = story["descr"]
        for rgx,rep in self.reader_rgx:
            s = rgx.sub(rep, s)

        f = lambda x,y : self.out(x, self.rfirsts(story, width), self.rmids(story, width), self.rends(story, width),\
                y, -1, width, [window])

        row = self.simple_out(self.reader_head(story, width), 0, -1, width, [window])
        row = f(s, row)
        if show_links:
            row = f("\n", row)
            for idx,link in enumerate(links):
                row = f(self.reader_link(idx, link), row)
        row = self.simple_out(self.reader_foot(story, width), row, -1, width, [window])
        return row

    def box(self, caption, width, window):
        s = u"─" * (width - (2 + tlen(caption)))
        row = self.simple_out(u"%B┌" + caption + s + u"┐\n", 0, -1, width, [window])
        row = self.simple_out(u"│" + " " * (width - 2) + u"│\n", row, -1, width, [window])
        row = self.simple_out(u"└" + u"─" * (width - 2) + u"┘%C", row, -1, width, [window])
        return row
