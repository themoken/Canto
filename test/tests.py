#!/usr/bin/python
# -*- coding: utf-8 -*-

#Canto - ncurses RSS reader
#   Copyright (C) 2008 Jack Miller <jack@codezen.org>
#
#   This program is free software; you can redistribute it and/or modify
#   it under the terms of the GNU General Public License version 2 as 
#   published by the Free Software Foundation.

import curses
from canto.widecurse import core

def test_widecurse():
    print "Testing widecurse"
    screen = curses.initscr()
    curses.noecho()
    curses.cbreak()
    screen.keypad(1)

    row = 0
    # Terminal styles
    core(screen, row, 0, 20, "Normal output", " ", "")
    row += 1

    core(screen, row, 0, 20, "%BBold output%b", " " , "")
    row += 1

    core(screen, row, 0, 20, "%UUnderline output%u", " " , "")
    row += 1

    core(screen, row, 0, 20, "%SStandout output%s", " " , "")
    row += 1

    core(screen, row, 0, 20, "%RReverse output%r", " " , "")
    row += 1

    core(screen, row, 0, 20, "%DDim output%d", " " , "")
    row += 1

    curses.start_color()

    # Color output
    for i in range(8):
        curses.init_pair(i + 1, i, 0)
        ouput = "%" + str(i + 1) + str(i + 1) + "%0"
        for off,attr in enumerate(["", "%B","%U","%S"]):
            core(screen, row, 0 + off, 20, \
                    attr + ouput + attr.lower(), " ", "")
        row += 1

    # Basic Color layering
    core(screen, row, 0, 20, "%B%11%22%33%44%55%04%03%02%01%b", " ", "")
    row += 1

    core(screen, row, 0, 20, "%8Cleanse the palette.", " " , "")
    row += 1

    # Multi-line Color layering and end escapes
    core(screen, row, 0, 20, "%2 This is the color 2", " ", "")
    row += 1

    core(screen, row, 0, 20, "This is color 2, too%0", " ", "")
    row += 1

    core(screen, row, 0, 20, "But not this", " ", "")
    row += 1

    # Empty string with repeating . ending in <><>
    core(screen, row, 0, 20, "", ".","<><>")
    row += 1

    # String of exact screen width
    core(screen, row, 0, 20, "12345678901234567890", " ", "")
    row += 1

    # String of exact screen witdth, after escapes
    core(screen, row, 0, 20, "%21234567890%51234567890", " " , "")
    row += 1

    # String too long
    ret = core(screen, row, 0, 20, "%812345678901234567890extra", " ", "")
    row += 1

    # Left over should be "extra"
    core(screen, row, 0, 20, "Left over: %s" % ret, " ", "")
    row += 1

    screen.refresh()
    screen.getch()
    curses.endwin()

from canto.canto_html import convert
def test_canto_html():
    print "Testing canto_html"
    print "1. Proper list nesting"

    text, links = convert("<ul><li>Unordered</li><li>Some header text"
            "<ol><li>Ordered</li><li>Also ordered</li></ol>"
            "<li>Unordered, too</li></ul>")

    if text != "\n%I\n● Unordered\n● Some header text\n%I\n1.Ordered"\
        "\n2.Also ordered%i\n\n● Unordered, too%i\n":
        print "FAILED"
    else:
        print "PASSED"

    print "\n2. Test link handler"

    text, links =  convert("""<a href="test">Blahblah</a>""")

    if links != [("%4Blahblah","test","browser")]:
        print "FAILED"
    else:
        print "PASSED"

    print "\n3. Test image handler"

    text,links = convert("""<img src="myimage.jpg" />
                        <img src="otherimage.jpg" alt="Sexy" />""")

    if links != [("image","myimage.jpg","image"),\
            ("Sexy","otherimage.jpg","image")]:
        print "FAILED"
    else:
        print "PASSED"

if __name__ == "__main__":
    test_widecurse()
    test_canto_html()
