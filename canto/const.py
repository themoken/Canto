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
UPDATE = 4
KEY_PASSTHRU = 5
REDRAW_ALL = 6
WINDOW_SWITCH = 7
REFILTER = 8
RETAG = 9
TFILTER = 10

STORY_SAVED = 0
STORY_UPDATED = 1
STORY_QD = 2

PROC_UPDATE = 0
PROC_FILTER = 1
PROC_BOTH = 2
PROC_TEST = 3
PROC_GETTAGS = 4
PROC_FLUSH = 5
PROC_KILL = 6
PROC_SYNC = 7
PROC_DEQD = 8

VERSION_TUPLE = SET_VERSION_TUPLE
GIT_SHA = SET_GIT_SHA
