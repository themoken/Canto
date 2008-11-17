#!/usr/bin/python

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

    print convert("<ul><li>Unordered</li><li>Some header text\
            <ol><li>Ordered</li><li>Also ordered</li></ol>\
            <li>Unordered, too</li></ul>")[0]

    print "\n2. Test link handler"

    print convert("""<a href="test">Blahblah</a>""")[1]

    print "\n3. Test image handler"

    print convert("""<img src="myimage.jpg" />
                        <img src="otherimage.jpg" alt="Sexy" />""")[1]

if __name__ == "__main__":
    test_canto_html()
