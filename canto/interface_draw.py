# -*- coding: utf-8 -*-

#Canto - ncurses RSS reader
#   Copyright (C) 2008 Jack Miller <jack@codezen.org>
#
#   This program is free software; you can redistribute it and/or modify
#   it under the terms of the GNU General Public License version 2 as 
#   published by the Free Software Foundation.


from widecurse import core, tlen
import canto_html

import locale
import re

class Renderer :
    def __init__(self):
        self.prefcode = locale.getpreferredencoding()

        self.story_rgx = [
            # Eliminate extraneous HTML
            (re.compile(u"<.*?>"), u""),
            (re.compile(u"&(\w{1,8});"), canto_html.ent_wrapper),
            (re.compile(u"&#([xX]?[0-9a-fA-F]+)[^0-9a-fA-F]"),
                canto_html.char_wrapper)
            ]

        self.reader_pre_rgx = []

        self.reader_post_rgx = [
            (re.compile(u"[\\\"](.*?)[\\\"]"), u"%5\"\\1\"%0"),
            ]

        self.bq = u"%B%1│%0%b "
        self.bq_on = 0

        self.indent = u"  "
        self.in_on = 0

    def tag_head(self, dict):
        t = u"%1" + dict["tag"].tag + u" [%2" + unicode(dict["tag"].unread)\
                + u"%0]%0"
        if dict["tag"].collapsed:
            if dict["tag"][0].selected():
                return [(u"%C%B%1 > " + t + u"", u" ", u" "),(u" ",u" ",u" ")]
            else:
                return [(u"%C%B   " + t + u"",u" ", u" "),(u" ",u" ",u" ")]

        return [(u"%B   " + t, u" ", u""),(u"%1┌", u"─", u"┐%C%0")]

    def tag_foot(self, dict):
        return [(u"%1%B└", u"─", u"┘%C%0")]

    def firsts(self, dict):
        base = u"%C%1%B│%b%0 "
    
        if dict["story"].selected() :
            if dict["cfg"].key_handlers[0].focus:
                base += u"%1%B>%b%0 "
            else:
                base += u"%1%B_%b%0 "
        else:
            base += u"  "

        if dict["story"].marked():
            base += u"%1%B"
        else:
            if dict["story"].wasread():
                base += u"%3"
            else:
                base += u"%2%B"

        return (base, u" ", u" %1%B│%b%0")

    def mids(self, dict):
        return (u"%1%B│%b%0      ", u" ", u" %1%B│%b%0")

    def ends(self, dict):
        return (u"%1%B│%b%0      ", u" ", u" %1%B│%b%0")

    def reader_head(self, dict):
        title = self.do_regex(dict["story"]["title"], self.story_rgx)
        return [(u"%1%B" + title, u" ", u" "),(u"%1┌",u"─",u"┐%C")]

    def reader_foot(self, dict):
        return [(u"%B└", u"─", u"┘%C")]

    def reader_link(self, idx, link):
        if link[2] == "link":
            color = u"%4"
        elif link[2] == "image":
            color = u"%7"
        else:
            color = u"%8"

        return color + u"[" + unicode(idx) + u"] " + \
                link[0] + u"%1 - " + link[1]

    def rfirsts(self, dict):
        return (u"%1%B│%b%0 ", u" ", u" %1%B│%b%0")

    def rmids(self, dict):
        return (u"%1%B│%b%0 ", u" ", u" %1%B│%b%0")
    
    def rends(self, dict):
        return (u"%1%B│%b%0 ", u" ", u" %1%B│%b%0")

    def __window(self, row, height, window_list):
        if height != -1:
            winidx, winrow = divmod(row, height)
            try :
                window = window_list[winidx]
            except IndexError:
                window = None
            return (window, winrow)
        else:
            return (window_list[0], row)

    def core_wrap(self, window, winrow, width, s, rep, end):
        ret = core(window, winrow, 0, width,
                s.encode(self.prefcode, 'replace'),
                rep.encode(self.prefcode, 'replace'),
                end.encode(self.prefcode, 'replace'))
        if ret:
            ret = unicode(ret, self.prefcode)
        return ret

    def tlen_wrap(self, s):
        return tlen(s.encode(self.prefcode, 'replace'))

    def simple_out(self, list, row, height, width, window_list):
        line = 0
        for s,rep,end in list:
            while s:
                 window, winrow = self.__window(row + line, height, window_list)
                 s = self.core_wrap(window, winrow, width, s, rep, end)
                 line += 1

        return row + line
               
    def out(self, list, row, height, width, window_list):
        line = 0
        for s, l in list:
            if s:

                # Handle block level style, not covered in widecurse.
                # This is broken into three sections so that styles
                # can be applied to a single line and applied in between.

                # Note, as with any unknown % escape, these will be
                # totally ignored in the middle of a line.

                # Toggle on based on start of line
                while s[:2] in [u"%Q",u"%I"]:
                    if s.startswith(u"%Q"):
                        self.bq_on += 1
                    else:
                        self.in_on += 1
                    s = s[2:]

                # Add decorations to firsts,mids,lasts
                if self.bq_on:
                    l = [(e[0] + self.bq * self.bq_on,\
                            e[1],e[2]) for e in l]
                if self.in_on:
                    l = [(e[0] + self.indent * self.in_on,\
                            e[1],e[2]) for e in l]
               
                # Toggle off based on end of line
                while s[-2:] in [u"%q",u"%i"]:
                    if s.endswith(u"%q"):
                        self.bq_on -= 1
                    else:
                        self.in_on -= 1
                    s = s[:-2]

            while s :
                window, winrow = self.__window(row + line, height, window_list)

                # First line, obviously use first line caps.
                if line == 0:
                    start, rep, end = l[0]
                
                # If line > 1 and we've got more than could be handled
                # with end_caps, use mid_caps

                elif self.tlen_wrap(s) > (width - (self.tlen_wrap(l[2][2]))):
                    start, rep, end = l[1]

                # Otherwise, use end_caps

                else:
                    start, rep, end = l[2]

                t = s
                s = self.core_wrap(window, winrow, width, start + s, rep, end)

                # Detect an infinite loop caused by start, and canto
                # trying to be smart about wrapping =).

                if s == t:
                    s = self.core_wrap(window, winrow, width, s, u" ",u"")
                line += 1

        return row + line

    def do_regex(self, target, rlist):
        s = target
        for rgx,rep in rlist:
            s = rgx.sub(rep,s)
        return s
    
    def story(self, cfg, tag, story, row, height, width, window_list):
        title = self.do_regex(story["title"], self.story_rgx)
        title = title.lstrip().rstrip()

        d = {"tag": tag, "story" : story, "cfg" : cfg }

        if story.idx == 0:
            row = self.simple_out(self.tag_head(d),\
                row, height, width, window_list)

        if not tag.collapsed:
            row = self.out([[title, (self.firsts(d), self.mids(d), \
                    self.ends(d))]],
                    row, height, width, window_list)
            
            if story.last:
                row = self.simple_out(self.tag_foot(d),\
                    row, height, width, window_list)
    
        return row

    def reader(self, cfg, story, width, show_links, window):
        s = story.get_text()

        enc_links = []
        if "enclosures" in story:
            for e in story["enclosures"]:
                enc_links.append((u"[%s]" % e["type"],
                        e["href"], "link"))

        d = {"story" : story, "cfg" : cfg }

        s = self.do_regex(s, self.reader_pre_rgx)
        s,links = canto_html.convert(s)
        s = self.do_regex(s, self.reader_post_rgx)

        links = [(u"main link", story["link"], "link")] + links
        links += enc_links

        l = s.split("\n")
        if show_links:
            l.append(" ")
            for idx,link in enumerate(links):
                l.append(self.reader_link(idx, link))

        row = self.simple_out(self.reader_head(d), 0, -1, width, [window])
        row = self.out([[x, (self.rfirsts(d), self.rmids(d),
            self.rends(d))] for x in l], row, -1, width, [window])
        row = self.simple_out(self.reader_foot(d), row, -1, width, [window])
        return row, links

    def status(self, bar, height, width, str):
        self.simple_out([(str, u" ", u"")], 0, height, width, [bar])
