#!/usr/bin/python
# -*- coding: utf-8 -*-

#Canto - ncurses RSS reader
#   Copyright (C) 2008 Jack Miller <jack@codezen.org>
#
#   This program is free software; you can redistribute it and/or modify
#   it under the terms of the GNU General Public License version 2 as 
#   published by the Free Software Foundation.

from canto_html import convert

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

    if links != [("Blahblah","test","browser","test")]:
        print "FAILED"
    else:
        print "PASSED"

    print "\n3. Test image handler"

    text,link = convert("""<img src="myimage.jpg" />
                        <img src="otherimage.jpg" alt="Sexy" />""")

    if links != [("[image]","myimage.jpg","images"),\
            ("Sexy","otherimage.jpg","images")]:
        print "FAILED"
    else:
        print "PASSED"

if __name__ == "__main__":
    test_canto_html()
