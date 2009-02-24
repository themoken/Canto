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
import sys

width_override = 0

class TestCurses(TestCase):
    def setUp(self):
        self.screen = curses.initscr()
        self.screen.erase()
        self.height, self.width = self.screen.getmaxyx()
        if width_override:
            self.width = width_override
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
    def setUp(self):
        TestCurses.setUp(self)
        for i,c in enumerate([7,4,3,2,5]):
            curses.init_pair(i + 1, c, 0)

        self.renderer = Renderer()
        self.row = 0
        
        self.ufp = {}
        self.ufp["title"] = u"Here, try an HTML entity on for size: &amp;"
        self.ufp["description"] =\
u"""Super long string description. With word wrapping and
line breaks
and slugified-huge-words-just-like-the-widecurses-test-has. Also
let's toss in some HTML, just for shits.
<p>
<pre><code>
    for(i=0;i &lt; n;i++) {
        //do something
        list[i] = list[i + 1];
    }
</code></pre>
</p>
<p>
<ol>
<li>Ordered 1</li>
<li>Ordered 2</li>
<li>Sublist <ul><li>Unordered 1</li><li>Unordered 2</li></ul>
<li>Ordered 4</li>
<li><strong>Styled Ordered 5</strong></li>
</ol>
<p>
<strong>Bold text</strong><br />
<em>Emphasis text</em>"""

        self.ufp["link"] = u"http://somelink"
        self.ufp["canto_state"] = [u"unread"]

        self.story = Story(self.ufp, None, self.renderer)
        self.story.idx = 0
        self.story.last = 1

        self.tag = Tag(None)

    def l(self, x):
        bme = ((""," ",""),(""," ",""),(""," ",""))
        self.row = self.renderer.out([(x, bme)], self.row, \
                self.height, self.width, [self.screen])
    
class TestIDrawBlocks(TestIDraw):
    def runTest(self):
        if self.width < 20:
            return

        self.width = 20
        # Simple quote
        self.l(u"%QThis is a quote%q")
        self.l(u" ")

        # Indent across a single line, that will break
        self.l(u"%IThis is uniformly indented broken line write.%i")
        self.l(u" ")

        # Multi line quote with forced breaks.
        self.l(u"%QThis is a")
        self.l(u"multi-line")
        self.l(u"quote%q")
        self.l(u" ")

class TestIDrawStory(TestIDraw):
    def runTest(self):
        self.renderer.story(None, self.tag, self.story, self.row, self.height,\
                self.width, [self.screen])

class TestIDrawReader(TestIDraw):
    def runTest(self):
        self.renderer.reader(None, self.story, self.width, 1, self.screen)

from canto.widecurse import core
class TestWidecurse(TestCurses):
    def l(self, x, r=" ", e=""):
        p = locale.getpreferredencoding()
        self.row += 1
        return core(self.screen, self.row, 0, self.width,\
                x.encode(p), 
                r.encode(p), 
                e.encode(p))

    def runTest(self):
        if self.width < 20:
            return

        self.width = 20
        # Terminal styles
        self.l(u"%8Normal output")
        self.l(u"%BBold output%b")
        self.l(u"%UUnderline output%u")
        self.l(u"%SStandout output%s")
        self.l(u"%RReverse output%r")
        self.l(u"%DDim output%d")
        
        # Color output
        for i in range(8):
            curses.init_pair(i + 1, i, 0)
            ouput = u"%" + unicode(i + 1) + unicode(i + 1) + u"%0"
            for off,attr in enumerate([u"", u"%B",u"%U",u"%S"]):
                core(self.screen, self.row, 0 + off, self.width, \
                        (attr + ouput +
                            attr.lower()).encode(locale.getpreferredencoding())\
                            , " ", "")
            self.row += 1

        # Basic Color layering
        self.l(u"%B%11%22%33%44%55%04%03%02%01%b")
        self.l(u"%8Cleanse the palette.")

        # Multi-line Color layering and end escapes
        self.l(u"%2 This is the color 2")
        self.l(u"This is color 2, too%0")
        self.l(u"But not this")

        # Empty string with repeating . ending in <><>
        self.l(u"", u".",u"<><>")

        # String of exact screen width
        self.l(u"12345678901234567890")

        # String of exact screen witdth, after escapes
        self.l(u"%21234567890%51234567890")

        # String too long
        r = self.l(u"%812345678901234567890extra")

        # Left over should be "extra"
        self.l(u"Left over: %s" % r)

        # Overflow the built-in color memory
        # This must be updated if color memory is increased
        self.l(u"%1z%2y%3x%4w%5v%6u%7t%8s%1r%2q%0a%0b%0c%0d%0e%0f%0g%0h%0i%0j")
        self.l(u" ")

        # Test word wrap
        s = u"%8A bunch of really short words, but more than one line."
        while s:
            s = self.l(s)

        self.l(u" ")

        # Test word breaking
        s = u"A-really-long-slugified-huge-word"
        while s:
            s = self.l(s)

from canto.canto_html import convert
class TestCantoHTML(TestCase):
    def runTest(self):
        # Test list nesting
        text, links = convert(u"<ul><li>Unordered</li><li>Some header text"
                u"<ol><li>Ordered</li><li>Also ordered</li></ol>"
                u"<li>Unordered, too</li></ul>")

        self.failUnless(text == u"\n%I\n\u25cf Unordered\n\u25cf "\
                u"Some header text\n%I\n1.Ordered\n2.Also ordered%i"\
                u"\n\n\u25cf Unordered, too%i\n")

        # Test LinkHandler
        text, links =  convert(u"""<a href="test">Blahblah</a>""")

        self.failUnless(links == [(u"%4Blahblah",u"test",u"link")])
        
        # Test ImageHandler
        text,links = convert(u"""<img src="myimage.jpg" />
                            <img src="otherimage.jpg" alt="Sexy" />""")

        self.failUnless(links == [(u"image",u"myimage.jpg",u"image"),\
                (u"Sexy",u"otherimage.jpg",u"image")])

if __name__ == "__main__":
    if len(sys.argv) > 1:
        try:
            width_override = int(sys.argv[1])
            sys.argv = sys.argv[:1]
        except:
            width_override = 0

    locale.setlocale(locale.LC_ALL, "")
    main()
