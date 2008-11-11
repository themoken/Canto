# -*- coding: utf-8 -*-
from widecurse import core, tlen
import html2text
import utility
import re

html2text.UNICODE_SNOB = 1
html2text.BODY_WIDTH = 0
html2text.SKIP_INTERNAL_LINKS = True

class Renderer :
    def __init__(self):
        self.story_rgx = [
            # Eliminate extraneous HTML
            (re.compile(u"<.*?>"), ""),

            # Eliminate HTML entities
            (html2text.r_unescape, html2text.replaceEntities)]

        self.reader_pre_rgx = [
            # Strip out newlines for formatting.
            (re.compile(u"<a\s+.*?>(.*?)</a\s*>"), u"%4\\1%1"),
            (re.compile(u"<img\s+.*?>"), u"[image]"),

            # Highlight quotes in color 5
            (re.compile(u"[\\\"](.*?)[\\\"]"), u"%5\\1%1")]

        # Most of these stem from not wanting to really change
        # the content of html2text (so it can be rebased)

        # The purpose of html2text is to generate markdown, which
        # is great and all, but not the best for display in the
        # reader.

        self.reader_post_rgx = []

        self.bq = "%B│%b"

    def tag_head(self, tag):
        t = "%1" + tag.tag + " [%2" + str(tag.unread) + "%1]"
        if tag.collapsed:
            if tag[0].selected():
                return [("%B%1 > " + t + "%C", " ", " "),(" "," "," ")]
            else:
                return [("%B   " + t + "%C"," ", " "),(" "," "," ")]

        return [("%B   " + t, " ", "%C"),("%1%B┌", "─", "┐%C")]

    def tag_foot(self, tag):
        return [("%1%B└", "─", "┘%C")]

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

        return (base, " ", " %1%B│%b%0")

    def mids(self, story):
        return ("%1%B│%b%0      ", " ", " %1%B│%b%0")

    def ends(self, story):
        return ("%1%B│%b%0      ", " ", " %1%B│%b%0")

    def reader_head(self, story):
        title = self.do_regex(story["title"], self.story_rgx)
        return [("%1%B" + title, " ", " "),("┌","─","┐%C")]

    def reader_foot(self, story):
        return [("%B└", "─", "┘%C")]

    def reader_link(self, idx, link):
        return "%4[" + str(idx) + "] " + link[1] + "%1 - " + link[0]

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
                 s = core(window, winrow, 0, width, s, rep, end)
                 line += 1

        return row + line
               
    def out(self, list, row, height, width, window_list):
        line = 0
        for s, l in list:
            if s and s[0] == ">":
                s = s[1:]
                l = [(e[0] + self.bq, e[1],e[2]) for e in l]

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

                t = s
                s = core(window, winrow, 0, width, start + s, rep, end)

                # Detect an infinite loop caused by start, and canto
                # trying to be smart about wrapping =).

                if s and s.endswith(t):
                    s = core(window, winrow, 0, width, s, " ","")
                line += 1

        return row + line

    def do_regex(self, target, rlist):
        s = unicode(target, "UTF-8")
        for rgx,rep in rlist:
            s = rgx.sub(rep,s)
        return s.encode("UTF-8")
    
    def story(self, tag, story, row, height, width, window_list):
        title = self.do_regex(story["title"], self.story_rgx)
        title = title.lstrip().rstrip()

        if story.idx == 0:
            row = self.simple_out(self.tag_head(tag),\
                row, height, width, window_list)

        if not tag.collapsed:
            row = self.out([[title, (self.firsts(story), self.mids(story), \
                    self.ends(story))]],
                    row, height, width, window_list)
            
            if story.last:
                row = self.simple_out(self.tag_foot(tag),\
                    row, height, width, window_list)
    
        return row

    def message(self, message, width, window):
        row = self.simple_out([("%B┌","─","┐")], 0, -1, width, [window])
        row = self.out([[message, [("%B│%b%1 ", " ", " %1%B│%b")]*3]], \
                row, -1, width, [window])
        row = self.simple_out([("└","─","┘%C")], row, -1, width, [window])
        return row

    def reader(self, story, width, links, show_links, window):
        if story.has_key("content"):
            s = story["content"][0]["value"]
        else:
            s = story["description"]

        s = self.do_regex(s, self.reader_pre_rgx)
        s = html2text.html2text(unicode(s, "UTF-8")).encode("UTF-8")
        s = self.do_regex(s, self.reader_post_rgx)

        l = s.split("\n")
        if show_links:
            l.append(" ")
            for idx,link in enumerate(links):
                l.append(self.reader_link(idx, link))

        row = self.simple_out(self.reader_head(story), 0, -1, width, [window])
        row = self.out([[x, (self.rfirsts(story), self.rmids(story),
            self.rends(story))] for x in l], row, -1, width, [window])
        row = self.simple_out(self.reader_foot(story), row, -1, width, [window])
        return row

    def box(self, caption, width, window):
        row = self.simple_out([("%B┌" + caption,"─","┐")], \
                0, -1, width, [window])
        row = self.simple_out([("│"," ","│")], row, -1, width, [window])
        row = self.simple_out([("└","─","┘%C")], row, -1, width, [window])
        return row
