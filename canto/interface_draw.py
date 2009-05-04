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

def draw_hooks(func):
    def new_func(self, *args):
        base = getattr(self, func.func_name + "_base", None)
        pre = getattr(self, "pre_" + func.func_name, [])
        post = getattr(self, "post_" + func.func_name, [])
        r = None

        if base:
            r = base(*args)
        for f in pre:
            r = f(*args)
        r = func(self, *args)
        for f in post:
            r = f(*args)
        return r

    return new_func

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

        self.pre_story = [
            self.story_strip_entities
            ]

        self.pre_reader = [
            self.reader_convert_html,
            self.reader_highlight_quotes,
            self.reader_add_main_link,
            self.reader_add_enc_links,
            self.reader_render_links,
            ]

        self.highlight_quote_rgx = re.compile(u"[\\\"](.*?)[\\\"]")

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
            base += u"%1%B>%b%0 "
        else:
            base += u"  "

        if dict["story"].was("marked"):
            base += u"%1%B"
        else:
            if dict["story"].was("read"):
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

    def story_base(self, dict):
        dict["content"] = dict["story"]["title"]

    def story_strip_entities(self, dict):
        dict["content"] = self.do_regex(dict["content"], self.story_rgx)
        dict["content"] = dict["content"].lstrip().rstrip()

    @draw_hooks
    def story(self, dict):
        d = {"tag": dict["tag"], "story" : dict["story"],\
                "cfg" : dict["tag"].cfg }

        row = dict["row"]
        if dict["story"].idx == 0:
            row = self.simple_out(self.tag_head(d),\
                row, dict["tag"].cfg.gui_height, \
                dict["width"], dict["window_list"])

        if not dict["tag"].collapsed:
            row = self.out([[dict["content"], (self.firsts(d), self.mids(d), \
                    self.ends(d))]],
                    row, dict["tag"].cfg.gui_height,\
                    dict["width"], dict["window_list"])
            
            if dict["story"].last:
                row = self.simple_out(self.tag_foot(d),\
                    row, dict["tag"].cfg.gui_height, \
                    dict["width"], dict["window_list"])
    
        return row

    def reader_base(self, dict):
        dict["content"] = dict["story"].get_text()

    def reader_convert_html(self, dict):
        dict["content"], dict["links"] = canto_html.convert(dict["content"])

    def reader_add_main_link(self, dict):
        dict["links"] = [(u"main link", dict["story"]["link"], "link")]\
                + dict["links"]

    def reader_add_enc_links(self, dict):
        if "enclosures" in dict["story"]:
            for e in dict["story"]["enclosures"]:
                dict["links"].append((u"[%s]" % e["type"],
                        e["href"], "link"))

    def reader_render_links(self, dict):
        if not dict["show_links"]:
            return

        dict["content"] += "\n"
        for idx, link in enumerate(dict["links"]):
            if link[2] == "link":
                color = u"%4"
            elif link[2] == "image":
                color = u"%7"
            else:
                color = u"%8"

            dict["content"] += color + u"[" + unicode(idx) + u"] " + \
                    link[0] + u"%1 - " + link[1] + "\n"

    def reader_highlight_quotes(self, dict):
        dict["content"] = self.highlight_quote_rgx.sub(u"%5\"\\1\"%0",\
                dict["content"])

    @draw_hooks
    def reader(self, dict):
        d = {"story" : dict["story"], "cfg" : dict["cfg"] }

        l = dict["content"].split("\n")
        row = self.simple_out(self.reader_head(d), 0, -1,\
                dict["width"], [dict["window"]])
        row = self.out([[x, (self.rfirsts(d), self.rmids(d),
            self.rends(d))] for x in l], row, -1,\
                dict["width"], [dict["window"]])
        row = self.simple_out(self.reader_foot(d), row, -1,\
                dict["width"], [dict["window"]])
        return row, dict["links"]

    def status(self, bar, height, width, str):
        self.simple_out([(str, u" ", u"")], 0, height, width, [bar])
