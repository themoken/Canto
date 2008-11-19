#!/usr/bin/python
# -*- coding: utf-8 -*-

#Canto - ncurses RSS reader
#   Copyright (C) 2008 Jack Miller <jack@codezen.org>
#
#   This program is free software; you can redistribute it and/or modify
#   it under the terms of the GNU General Public License version 2 as 
#   published by the Free Software Foundation.

from unittest import TestCase, TestSuite, main
from canto.widecurse import core
import curses

class TestCurses(TestCase):
    def setUp(self):
        self.screen = curses.initscr()
        curses.start_color()
        curses.noecho()
        curses.cbreak()
        self.screen.keypad(1)

    def tearDown(self):
        self.screen.getch()
        curses.endwin()

class TestWidecurse(TestCurses):
    def l(self, x, r=" ", e=""):
        self.row += 1
        return core(self.screen, self.row, 0, 20, x, r, e)

    def runTest(self):
        self.row = -1

        # Terminal styles
        self.l("Normal output")
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
        ret = self.l("%812345678901234567890extra")

        # Left over should be "extra"
        self.l("Left over: %s" % ret)
        self.screen.refresh()


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
    main()
