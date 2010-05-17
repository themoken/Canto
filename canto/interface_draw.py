# -*- coding: utf-8 -*-

#Canto - ncurses RSS reader
#   Copyright (C) 2008 Jack Miller <jack@codezen.org>
#
#   This program is free software; you can redistribute it and/or modify
#   it under the terms of the GNU General Public License version 2 as 
#   published by the Free Software Foundation.

# Interface_draw comprises the python base of canto's drawing code. The Renderer
# class is the object wrapper around canto's C extension (where all of the
# actual ncurses drawing is done).

# The Renderer class contains functions to draw each of the main components of
# the interface. The reader, the story list and the message status. In < 0.7.0
# the entire class had to be overridden in what amounted to an overly complex
# way to do *anything*.

# In >= 0.7.0, each of these functions is augmented with a series of hooks that
# affect the content that's going to be drawn. So where in 0.6.x the reader()
# function would explicitly render the content to HTML and insert the links and
# display to the screen, >= 0.7.0 decorates the reader() function with a number
# of auxiliary functions that amount to doing the same thing by default but are
# much easier to modify. One call to reader() turns into something like this:

# reader_base               -> adds the basic, unmodified text to the dict
# reader_convert_html       -> converts any HTML elements in the text, grabs
#                               links out as well.
# reader_highlight_quotes   -> highlights the quotes with color %5
# reader_add_main_link      -> adds the story link to links from convert_html
# reader_add_enc_links      -> adds any enclosure links to links
# reader_render_links       -> actually adds the content to
# reader                    -> finally actually perform the write

# This is all done transparently. Each of these functions takes a single dict
# that can be added to transparently. So, when someone  wants to add some
# information, they only need to write a function that takes a dict and
# manipulates the data in it, and insert it into the hooks. Much simpler than
# overriding a Python class. For an example of how that works, see the
# add_hook*/add_info functions in canto.extra.

# The dict, after the _base() call, contains:
#   dict["content"] -> the text (either the story title or story description)
#   dict["story"]   -> the relevant Story() object
#   dict["tag"]     -> the tag that the story is in
#   dict["cfg"]     -> Canto's Cfg() object

# There may be other particulars in there, but they're more for use in the
# drawing than to be modified on the fly.

# A call to story() is similarly augmented.

# The hooks are capable of doing post_hooks as well, which take place after the
# content is drawn. These aren't used by default, but could be used to perform
# any tear-down from more complex pre_hooks.

from widecurse import core, tlen
import canto_html

import locale
import re

# The draw_hooks decorator is what actually turns a single reader or story call
# in the succession of calls. 

def draw_hooks(func):
    def new_func(self, *args):
        # Hooray for Python introspection.
        base = getattr(self, func.func_name + "_base", None)
        pre = getattr(self, "pre_" + func.func_name, [])
        post = getattr(self, "post_" + func.func_name, [])
        r = None

        # Base function to set dict["content"]
        if base:
            base(*args)

        # Pre hooks
        for f in pre:
            f(*args)

        # The actual expected call
        r = func(self, *args)

        # Post hooks
        for f in post:
            f(*args)

        return r

    return new_func

# The BaseRenderer class, to ensure that any custom renderer is going to have
# all the necessary functions.

class BaseRenderer :
    def status(self, bar, height, width, str):
        pass
    def reader(self, dict):
        pass
    def story(self, dict):
        pass

# The main Renderer class.
# As mentioned above, the reader() and story() calls are augmented with hooks.
# These only handle content. The remainder of the drawing logic (the code that
# draws the pretty boxes and the tag headers on top of the first items) is
# handled by 5 functions for the story list and 5 functions for the reader.

# Story list
#   tag_head        -> draws the top of each tag
#       firsts      -> draws the first line of each item
#       mids        -> draws the middle lines of each item
#       ends        -> draws the last line of each item
#   tag_foot        -> draws the bottom of each tag

# The reader's corresponding functions are reader_{head, foot} and
# r{firsts, mids, ends}. In the case that there's only one line, only the
# firsts() functions are used, so it's not guaranteed that any function but that
# one will be called.

# All of these functions return tuples of three items:

#       (head, repeat, end)

# Where head is the left content, end is the right content, and repeat is the
# string repeated to fill the gap.

# The head and foot functions return a list of them, each one assumed to be a
# new line.

class Renderer(BaseRenderer):
    def __init__(self):
        self.htmlrenderer = canto_html.CantoHTML()
        self.prefcode = locale.getpreferredencoding()

        # These are used by the story pre_hook "strip_entities"
        self.story_rgx = [
            # Eliminate extraneous HTML
            (re.compile(u"<.*?>"), u""),
            (re.compile(u"&(\w{1,8});"), self.htmlrenderer.ent_wrapper),
            (re.compile(u"&#([xX]?[0-9a-fA-F]+)[^0-9a-fA-F]"),
                self.htmlrenderer.char_wrapper)
            ]

        # Default hook definitions
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

	# Call the initialization hook.
	self.init_hook()

    def tag_head(self, dict):
        t = u"%1" + dict["tag"].tag + u" [%2" + unicode(dict["tag"].unread)\
                + u"%0]%0"
        if dict["tag"].collapsed:
            if dict["tag"][0].selected():
                return [(u"%C%B%1 > " + t + u"", u" ", u" "),(u" ",u" ",u" ")]
            else:
                return [(u"%C%B   " + t + u"",u" ", u" "),(u" ",u" ",u" ")]

        return [(u"%B   " + t, u" ", u""),(u"%1┌", u"─", u"┐%C%0")]

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

    def tag_foot(self, dict):
        return [(u"%1%B└", u"─", u"┘%C%0")]

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


    # __window converts a virtual row into a window and an offset row. So if
    # you're got two columns that are 80 lines long, __window called with row 82
    # will return window_list[1], row 1.

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

    # The core_wrap and tlen_wrap functions exist to handle the encoding of
    # content to an encoding that can be printed to the terminal. Both take
    # unicode and return unicode, so aside from when the config / args are
    # parsed, this is the only place that canto deals with non-Unicode data.

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

    # simple_out is a simple drawing function that has no overhead for doing
    # complicated stuff like block level formatting. It also only handles a
    # single (h, r, e) tuple. This is useful for drawing heads/feet where all of
    # the formatting is already done and only one (h, r, e) tuple is used.

    def simple_out(self, list, row, height, width, window_list):
        line = 0
        for s,rep,end in list:
            while s:
                 window, winrow = self.__window(row + line, height, window_list)
                 s = self.core_wrap(window, winrow, width, s, rep, end)
                 line += 1

        return row + line

    # out is a much more complex drawing function. It does block level
    # formatting and takes a list of lines associated with an (h, r, e) tuple.
    # This is used for all of the real content. See reader() or story() for use.

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

    # *** From here out, it's all story, reader, status and associated hooks.

    def do_regex(self, target, rlist):
        s = target
        for rgx,rep in rlist:
            s = rgx.sub(rep,s)
        return s

    def story_base(self, dict):
        if dict["story"]["title"]:
            dict["content"] = dict["story"]["title"]
        else:
            dict["content"] = "%B%b"
        dict["type"] = dict["story"].get_title_type()

    def story_strip_entities(self, dict):
        if "html" in dict["type"]:
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
        dict["type"] = dict["story"].get_type()

    def reader_convert_html(self, dict):
        if "html" in dict["type"]:
            dict["content"], dict["links"] = \
                    self.htmlrenderer.convert(dict["content"])
        else:
            dict["links"] = []

    def reader_add_main_link(self, dict):
        dict["links"] = [(u"main link", dict["story"]["link"], "link")]\
                + dict["links"]

    def reader_add_enc_links(self, dict):
        if "enclosures" in dict["story"]:
            for e in dict["story"]["enclosures"]:
                if "type" not in e:
                    e["type"] = "unknown"
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

    def init_hook(self):
	# Do nothing. Override this in your own renderer.
	return 0
