#!/usr/bin/python
# -*- coding: utf-8 -*-

#Canto - ncurses RSS reader
#   Copyright (C) 2008 Jack Miller <jack@codezen.org>
#
#   This program is free software; you can redistribute it and/or modify
#   it under the terms of the GNU General Public License version 2 as 
#   published by the Free Software Foundation.

from unittest import TestCase, main
import curses
import locale

class TestCurses(TestCase):
    def setUp(self):
        self.screen = curses.initscr()
        curses.start_color()
        curses.init_pair(1, 7, 0)

        curses.noecho()
        curses.cbreak()
        self.screen.keypad(1)
        self.row = -1

    def tearDown(self):
        self.screen.refresh()
        self.screen.getch()
        curses.endwin()

from canto.interface_draw import Renderer
from canto.story import Story
from canto.tag import Tag
class TestIDraw(TestCurses):
    def l(self, x):
        bme = ((""," ",""),(""," ",""),(""," ",""))
        self.row = self.renderer.out([(x, bme)], self.row, \
                100, 20, [self.screen])
    
    def runTest(self):
        self.renderer = Renderer()
        self.row = 0

        # Simple quote
        self.l("%QThis is a quote%q")
        self.l(" ")

        # Indent across a single line, that will break
        self.l("%IThis is uniformly indented broken line write.%i")
        self.l(" ")

        # Multi line quote with forced breaks.
        self.l("%QThis is a")
        self.l("multi-line")
        self.l("quote%q")
        self.l(" ")
        
        # Test some story rendering cases. The reader rendering
        # will be handled separately.

        ufp = {}
        ufp["title"] = "Here, try an HTML entity on for size: &amp;"
        ufp["canto_state"] = ["unread"]

        story = Story(ufp, None, self.renderer)
        story.idx = 0
        story.last = 1

        tag = Tag()

        self.renderer.story(tag, story, self.row, 100, 20, [self.screen])

from canto.widecurse import core
class TestWidecurse(TestCurses):
    def l(self, x, r=" ", e=""):
        self.row += 1
        return core(self.screen, self.row, 0, 20, x, r, e)

    def runTest(self):
        # Terminal styles
        self.l("%8Normal output")
        self.l("%BBold output%b")
        self.l("%UUnderline output%u")
        self.l("%SStandout output%s")
        self.l("%RReverse output%r")
        self.l("%DDim output%d")
        
        # Color output
        for i in range(8):
            curses.init_pair(i + 1, i, 0)
            ouput = "%" + str(i + 1) + str(i + 1) + "%0"
            for off,attr in enumerate(["", "%B","%U","%S"]):
                core(self.screen, self.row, 0 + off, 20, \
                        attr + ouput + attr.lower(), " ", "")
            self.row += 1

        # Basic Color layering
        self.l("%B%11%22%33%44%55%04%03%02%01%b")
        self.l("%8Cleanse the palette.")

        # Multi-line Color layering and end escapes
        self.l("%2 This is the color 2")
        self.l("This is color 2, too%0")
        self.l("But not this")

        # Empty string with repeating . ending in <><>
        self.l("", ".","<><>")

        # String of exact screen width
        self.l("12345678901234567890")

        # String of exact screen witdth, after escapes
        self.l("%21234567890%51234567890")

        # String too long
        r = self.l("%812345678901234567890extra")

        # Left over should be "extra"
        self.l("Left over: %s" % r)

        # Overflow the built-in color memory
        # This must be updated if color memory is increased
        self.l("%1z%2y%3x%4w%5v%6u%7t%8s%1r%2q%0a%0b%0c%0d%0e%0f%0g%0h%0i%0j")
        self.l(" ")

        # Test word wrap
        s = "%8A bunch of really short words, but more than one line."
        while s:
            s = self.l(s)

        self.l(" ")

        # Test word breaking
        s = "A-really-long-slugified-huge-word"
        while s:
            s = self.l(s)

from canto.canto_html import convert
class TestCantoHTML(TestCase):
    def runTest(self):
        # Test list nesting
        text, links = convert("<ul><li>Unordered</li><li>Some header text"
                "<ol><li>Ordered</li><li>Also ordered</li></ol>"
                "<li>Unordered, too</li></ul>")

        self.failUnless(text == "\n%I\n● Unordered\n● Some header text\n"\
            "%I\n1.Ordered\n2.Also ordered%i\n\n● Unordered, too%i\n")

        # Test LinkHandler
        text, links =  convert("""<a href="test">Blahblah</a>""")

        self.failUnless(links == [("%4Blahblah","test","browser")])
        
        # Test ImageHandler
        text,links = convert("""<img src="myimage.jpg" />
                            <img src="otherimage.jpg" alt="Sexy" />""")

        self.failUnless(links == [("image","myimage.jpg","image"),\
                ("Sexy","otherimage.jpg","image")])

if __name__ == "__main__":
    locale.setlocale(locale.LC_ALL, "")
    main()
