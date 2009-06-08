# -*- coding: utf-8 -*-

#Canto - ncurses RSS reader
#   Copyright (C) 2008 Jack Miller <jack@codezen.org>
#
#   This program is free software; you can redistribute it and/or modify
#   it under the terms of the GNU General Public License version 2 as 
#   published by the Free Software Foundation.

UPDATE_FIRST = 1
CHECK_NEW = 2
FEED_LIST = 4
OUT_OPML = 8
IN_OPML = 16
IN_URL = 32

EXIT = -1
NOKEY = 0
REFRESH_ALL = 1
READER_NEXT = 2
READER_PREV = 3
ALARM = 4
KEY_PASSTHRU = 5
REDRAW_ALL = 6
WINDOW_SWITCH = 7
REFILTER = 8
RETAG = 9
TFILTER = 10

THREAD_UPDATE = 0
THREAD_FILTER = 1
THREAD_BOTH = 2

VERSION_TUPLE = SET_VERSION_TUPLE
GIT_SHA = SET_GIT_SHA
