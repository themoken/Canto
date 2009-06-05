# -*- coding: utf-8 -*-

#Canto - ncurses RSS reader
#   Copyright (C) 2008 Jack Miller <jack@codezen.org>
#
#   This program is free software; you can redistribute it and/or modify
#   it under the terms of the GNU General Public License version 2 as 
#   published by the Free Software Foundation.

import curses

def convkey(s):
    if len(s) == 1:
        return (ord(s),0)
    elif s.startswith("C-"):
        k, m = convkey(s[2:])
        return (k & 0x1F, m) 

    elif s.startswith("M-"):
        k, m = self.convkey(s[2:])
        return (k, 1)

    elif s == "KEY_RETURN":
        return (10, 0)
    else:
        return (getattr(curses, s), 0)

def conv_key_list(dict):
    ret = {}
    for key in dict:
        if not dict[key]:
            continue

        try:
            newkey = convkey(key)
        except AttributeError:
            continue

        if type(dict[key]) != type([]):
            ret[newkey] = [dict[key]]
        else:
            ret[newkey] = dict[key]

    return ret

def register(c):
    c.key_list = {
         "q" : "quit",
         "KEY_DOWN" : "next_item",
         "KEY_UP" : "prev_item",
         "j" : "next_item",
         "k" : "prev_item",
         "KEY_RIGHT" : "just_read",
         "KEY_LEFT" : "just_unread",
         "KEY_NPAGE" : "next_tag",
         "KEY_PPAGE" : "prev_tag",
         "[" : "prev_filter",
         "]" : "next_filter",
         "{" : "prev_tag_filter",
         "}" : "next_tag_filter",
         "-" : "prev_tag_sort",
         "=" : "next_tag_sort",
         "l" : "next_tag",
         "o" : "prev_tag",
         "<" : "prev_tagset",
         ">" : "next_tagset",
         "g" : "goto",
         "." : "next_unread",
         "," : "prev_unread",
         "f" : "inline_search",
         "n" : "next_mark",
         "p" : "prev_mark",
         " " : ["just_read", "reader"],
         "c" : "toggle_collapse_tag",
         "C" : "set_collapse_all",
         "V" : "unset_collapse_all",
         "m" : "toggle_mark",
         "M" : "all_unmarked",
         "r" : "tag_read",
         "R" : "all_read",
         "u" : "tag_unread",
         "U" : "all_unread",
         ";" : "goto_reltag",
         ":" : "goto_tag",
         "C-r" : "force_update",
         "C-l" : "refresh",
         "h" : "help"}
        
    c.reader_key_list = {
         "KEY_DOWN" : "scroll_down",
         "KEY_UP" : "scroll_up",
         "j" : "scoll_down",
         "k" : "scroll_up",
         "KEY_NPAGE" : "page_down",
         "KEY_PPAGE" : "page_up",
         "g" : "goto",
         "l" : "toggle_show_links",
         "n" : ["destroy","next_item","reader"],
         "p" : ["destroy","prev_item","reader"],
         "h" : ["destroy","help"],
         "q" : ["destroy","quit"],
         " " : "destroy"}

    c.locals.update({
         "keys" : c.key_list,
         "reader_keys" : c.reader_key_list })

def post_parse(c):
    c.key_list = conv_key_list(c.key_list)
    c.reader_key_list = conv_key_list(c.reader_key_list)

def validate(c):
    pass

def test(c):
    pass
