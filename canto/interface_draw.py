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

    def tag_head(self, tag):
        t = "%1" + tag.tag.encode("UTF-8") + " [%2" + str(tag.unread) + "%0]"
        if tag.collapsed:
            if tag[0].selected():
                return [("%B > " + t + "%C", " ", " "),(" "," "," ")]
            else:
                return [("%B   " + t + "%C)"," ", " "),(" "," "," ")]
        
        return [("%B   " + t, " ", "%C"),("%B┌", "─", "┐%C")]

    def tag_foot(self, tag):
        return [("%B└", "─", "┘%C\n")]

    def firsts(self, story):
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

        return (base, " ", " %1%B│%b")

    def mids(self, story):
        return ("%B│%b%0      ", " ", " %1%B│%b")

    def ends(self, story):
        return ("%B│%b%0      ", " ", " %1%B│%b")

    def reader_head(self, story):
        return [("%1%B" + story["title"], " ", " "),("┌","─","┐%C\n")]

    def reader_foot(self, story):
        return [("%B└", "─", "┘%C\n")]

    def reader_link(self, idx, link):
        return "%4[" + str(idx) + "] " + link[1] + "- %1" + link[0]

    def rfirsts(self, story):
        return ("%B│%b%1 ", " ", " %1%B│%b")

    def rmids(self, story):
        return ("%B│%b%0 ", " ", " %1%B│%b")
    
    def rends(self, story):
        return ("%B│%b%0 ", " ", " %1%B│%b")

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

    def simple_out(self, list, row, height, width, window_list):
        line = 0
        for s,rep,end in list:
            while s:
                 window, winrow = self.__window(row + line, height, window_list)
                 s = core(window, winrow, 0, width, s, rep, end)[0]
                 line += 1

        return row + line
               
    def out(self, list, row, height, width, window_list):
        line = 0
        for s, l in list:
            while s :
                window, winrow = self.__window(row + line, height, window_list)

                # First line, obviously use first line caps.
                if line == 0:
                    start, rep, end = l[0]
                
                # If line > 1 and we've got more than could be handled
                # with end_caps, use mid_caps

                elif tlen(s) > (width - (tlen(l[2][2]))):
                    start, rep, end = l[1]

                # Otherwise, use end_caps

                else:
                    start, rep, end = l[2]

                s = core(window, winrow, 0, width, start + s, rep, end)[0]
                line += 1

        return row + line

    def story(self, tag, story, row, height, width, window_list):
        if story.idx == 0:
            row = self.simple_out(self.tag_head(tag),\
                row, height, width, window_list)

        if not tag.collapsed:
            row = self.out([[story["title"], (self.firsts(story), self.mids(story), self.ends(story))]],
                    row, height, width, window_list)
            
            if story.last:
                row = self.simple_out(self.tag_foot(tag),\
                    row, height, width, window_list)
    
        return row

    def reader(self, story, width, links, show_links, window):
        s = story["descr"]
        for rgx,rep in self.reader_rgx:
            s = rgx.sub(rep, s)
        
        row = self.simple_out(self.reader_head(story), 0, -1, width, [window])

        l = s.split("\n")
        if show_links:
            l.append(" ")
            for idx,link in enumerate(links):
                l.append(self.reader_link(idx, link))

        row = self.out([[x, (self.rfirsts(story), self.rmids(story), self.rends(story))] for x in l], row, -1, width, [window])
        row = self.simple_out(self.reader_foot(story), row, -1, width, [window])
        return row

    def box(self, caption, width, window):
        row = self.simple_out([("%B┌" + caption,"─","┐")], 0, -1, width, [window])
        row = self.simple_out([("│"," ","│")], row, -1, width, [window])
        row = self.simple_out([("└","─","┘%C")], row, -1, width, [window])
        return row
