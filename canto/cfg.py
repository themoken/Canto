# -*- coding: utf-8 -*-

#Canto - ncurses RSS reader
#   Copyright (C) 2008 Jack Miller <jack@codezen.org>
#
#   This program is free software; you can redistribute it and/or modify
#   it under the terms of the GNU General Public License version 2 as 
#   published by the Free Software Foundation.

import interface_draw
import utility
import feed

import xml.parsers.expat
import traceback
import chardet
import codecs
import os

class Cfg:
    def __init__(self, conf, log_file, feed_dir, script_dir):
        self.handlers = {
            "browser" : { None : ("firefox \"%u\"", 0, 0) },
            "image" : {}
        }

        self.wait_for_pid = 0
        self.log_file = log_file

        # A MYRIAD of defaults. Bwahaha.

        self.key_list = {"q" : "quit",
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
                         "{" : "prev_feed_filter",
                         "}" : "next_feed_filter",
                         "l" : "next_tag",
                         "o" : "prev_tag",
                         "g" : "goto",
                         "." : "next_unread",
                         "," : "prev_unread",
                         "f" : "inline_search",
                         "n" : "next_mark",
                         "p" : "prev_mark",
                         " " : "reader",
                         "c" : "toggle_collapse_tag",
                         "C" : "set_collapse_all",
                         "V" : "unset_collapse_all",
                         "m" : "toggle_mark",
                         "M" : "all_unmarked",
                         "r" : "tag_read",
                         "R" : "all_read",
                         "u" : "tag_unread",
                         "U" : "all_unread",
                         ":" : "command",
                         "C-r" : "force_update",
                         "C-l" : "refresh",
                         "\t" : "switch",
                         "h" : "help"}
        
        self.reader_key_list = {"KEY_DOWN" : "scroll_down",
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
                              "\t" : "switch",
                              " " : ["quit", "switch"]}

        self.colors = [("white","black"),("blue","black"),("yellow","black"),
                ("green","black"),("pink","black"),("black","black"),("blue","black"),(0,0)]

        self.default_rate = 5
        self.default_keep = 40
        self.default_filterlist = [None]
        self.default_sort = None
        self.default_renderer = interface_draw.Renderer()
        self.default_msg_tick = 5

        # Key handlers is a stack-like list that contains all "inputs"
        # that can take keys from the user. Generally, this is every
        # graphical class open at a time. The last item being the top
        # window, receiving keys.

        self.key_handlers = []
        self.cur_kh = -1

        self.path = conf
        self.feed_dir = feed_dir
        self.script_dir = script_dir

        self.columns = 1
        self.height = 0
        self.width = 0

        self.gui_top = 0
        self.gui_right = 0
        self.gui_height = 0
        self.gui_width = 0

        self.msg_height = 1
        self.msg = None
        self.msg_tick = 0

        self.status = self.default_status

        self.reader_lines = 0
        self.reader_orientation = None

        self.resize_hook = None
        self.new_hook = None
        self.select_hook = None
        self.unselect_hook = None
        self.start_hook = None
        self.end_hook = None
        self.update_hook = None

        self.filterlist = [None]
        self.filter_idx = 0

        self.no_conf = 0

        # If we can't stat self.path, generate a default config
        # and toss a message about making your own.

        try :
            os.stat(self.path)
        except :
            print "Unable to find config file. Generating and "\
                  "using ~/.canto/conf.example"
            print "You will keep getting this until you create your "\
                  "own ~/.canto/conf"
            print "\nRemember: it's 'h' for help.\n"

            newpath = os.getenv("HOME") + "/.canto/"
            if not os.path.exists(newpath):
                os.mkdir(newpath)

            self.path = newpath + "conf.example"
            f = codecs.open(self.path, "w", "UTF-8")
            f.write("# Auto-generated by canto because you don't have one.\n"
                    "# Please copy to/create ~/.canto/conf\n\n")
            f.write("""addfeed("Slashdot", """\
                    """"http://rss.slashdot.org/slashdot/Slashdot")\n""")
            f.write("""addfeed("Reddit", """\
                    """"http://reddit.com/.rss")\n""")
            f.write("""addfeed("KernelTrap", """\
                    """"http://kerneltrap.org/node/feed")\n""")
            f.write("""addfeed("Canto", """\
                    """"http://codezen.org/canto/feeds/latest")\n""")
            f.write("\n")
            f.close()
            self.no_conf = 1

        self.feeds = []
        self.parse()

        # Convert all of the C-M-blah (human readable) keys into
        # key tuples used in the main loop.

        self.key_list = utility.conv_key_list(self.key_list)
        self.reader_key_list = utility.conv_key_list(self.reader_key_list)

    def message(self, s, time=0):
        if self.msg:
            self.default_renderer.status(self.msg, self.msg_height,\
                    self.width, s)
            if not time:
                self.msg_tick = self.default_msg_tick
            else:
                self.msg_tick = time
            self.msg.refresh()

    # Simple append log.

    def log(self, message, mode="a"):
        self.message(message)
        try:
            f = open(self.log_file, mode)
            f.write(message + "\n")
            f.close()
        except:
            pass

    # wrap_args wraps each filter class in the filter_dec wrapper
    # and ensures that sort is a list.

    def wrap_args(self, kwargs):
        if kwargs.has_key("filterlist"):
            kwargs["filterlist"] = \
                    [self.filter_dec(x) for x in kwargs["filterlist"]]
        if kwargs.has_key("sort"):
            if type(kwargs["sort"]) != type([]):
                kwargs["sort"] = [kwargs["sort"]]
            kwargs["sort"] = [self.hook_dec(x) for x in kwargs["sort"]]

        return kwargs

    # Addfeed is a wrapper that's called as the config is exec'd
    # so that subsequent commands can reference it ASAP, and
    # so that set defaults are applied at that point.

    def addfeed(self, tag, URL, **kwargs):
        if (not URL) or URL == "":
            return -1

        for key in ["keep","rate","renderer","filterlist","sort"]:
            if not key in kwargs:
                kwargs[key] = getattr(self, "default_" + key)

        for key in ["username","password"]:
            if not key in kwargs:
                kwargs[key] = None

        kwargs = self.wrap_args(kwargs)

        # The tag is the only thing that has to be unique, so we ignore
        # any duplicate URLs, or everything  will break.

        if not URL in [f.URL for f in self.feeds]:
            self.feeds.append(feed.Feed(self, self.feed_dir +\
                    URL.replace("/", " "), tag, URL,\
                    kwargs["rate"],\
                    kwargs["keep"],\
                    kwargs["renderer"],\
                    kwargs["filterlist"],\
                    kwargs["sort"],
                    kwargs["username"],
                    kwargs["password"]))
            return 1
        return -1

    def set_default_sort(self, list):
        self.default_sort = list

    def set_default_filterlist(self, list):
        self.default_filterlist = list

    def set_default_rate(self, rate):
        self.default_rate = rate

    def set_default_keep(self, keep):
        self.default_keep = keep

    def set_default_renderer(self, renderer):
        self.default_renderer = renderer

    def change_feed(self, tag, **kwargs):
        l = [f for f in self.feeds if f.tag == tag]
        if not len(l):
            return

        kwargs = self.wrap_args(kwargs)

        feed = l[0]
        for key in ["keep","rate","renderer","filterlist","sort"]:
            if kwargs.has_key(key):
                setattr(feed, key, kwargs[key])

    # This decorator-like function is used to wrap
    # all of the hooks, so that user exceptions don't
    # take Canto down.

    def hook_dec(self, fn):
        if not fn:
            return None

        def hdec(*args):
            try:
                r = fn(*args)
            except:
                self.log("\nException in hook:")
                self.log("%s" % traceback.format_exc())
                return 0
            return r
        return hdec

    def filter_dec(self, c):
        if not c:
            return None

        class fdec():
            def __init__(self, instance, log):
                self.instance = instance
                self.log = log

            def __str__ (self):
                return self.instance.__str__()

            def __call__(self, *args):
                try:
                    return self.instance(*args)
                except:
                    self.log("\nException in filter:")
                    self.log("%s" % traceback.format_exc())
        return fdec(c, self.log)

    def read_decode(self, filename):
        try:
            data = codecs.open(filename, "r", "UTF-8").read()
        except UnicodeDecodeError:
            # If the Python built-in decoders can't figure it
            # out, it might need some help from chardet.
            data = codecs.open(self.path, "r").read()
            enc = chardet.detect(data)["encoding"]
            data = unicode(data, enc).encode("UTF-8")
            self.log("Chardet detected encoding %s for %s" % (enc,filename))
        return data

    def parse(self):

        locals = {"addfeed":self.addfeed,
            "add_feed":self.addfeed,
            "change_feed":self.change_feed,
            "default_sort" : self.set_default_sort,
            "default_filterlist" : self.set_default_filterlist,
            "default_rate" : self.set_default_rate,
            "default_keep" : self.set_default_keep,
            "default_renderer" : self.set_default_renderer,
            "renderer" : interface_draw.Renderer,
            "keys" : self.key_list,
            "reader_keys" : self.reader_key_list,
            "reader_orientation" : self.reader_orientation,
            "reader_lines" : self.reader_lines,
            "columns" : self.columns,
            "colors" : self.colors,
            "source_opml" : self.source_opml,
            "source_urls" : self.source_urls,
            "link_handler" : self.link_handler,
            "image_handler" : self.image_handler}

        # The entirety of the config is read in first (rather
        # than using execfile) because the config could be in
        # some strange encoding, and execfile would choke attempting
        # to coerce some character into ASCII.
        data = self.read_decode(self.path)

        try :
            exec(data, {}, locals)
        except :
            print "Invalid line in config."
            traceback.print_exc()
            raise

        # exec cannot modify basic type
        # locals directly, so we do it by hand.

        for attr in ["filterlist", "filter_idx", "render", "columns",\
                "reader_orientation", "reader_lines"]:
            if locals.has_key(attr):
                setattr(self, attr, locals[attr])

        # Wrap hooks in the exception handler
        for hook in ["resize_hook","new_hook","select_hook","update_hook",\
                "unselect_hook","start_hook","end_hook"]:
            if locals.has_key(hook):
                setattr(self, hook, self.hook_dec(locals[hook]))

        # Wrap filters in exception handler
        self.filterlist = [self.filter_dec(x) for x in self.filterlist]

        # Ensure we have at least one column
        if not self.columns:
            self.log("columns <1, set to 1")
            self.columns = 1

        # And that the user didn't set filter_idx invalidly.
        if self.filter_idx >= len(self.filterlist):
            self.log("filter_idx not in range, set to 0")
            self.filter_idx = 0

    def source(fn):
        def source_dec(self, *args, **kwargs):
            append = False
            if kwargs.has_key("append"):
                append = kwargs["append"]
                file = open(self.path, "a")

            l = fn(self, *args, **kwargs)

            for f in l:
                if self.addfeed(f[0],f[1]) and append:
                    if f[0]:
                        file.write("""add_feed("%s","%s")\n""" % f) 
                    else:
                        file.write("""add_feed(None,"%s")\n""" % f[1])

            if append:
                file.close()
        return source_dec
   
    @source
    def source_opml(self, filename, **kwargs):
        l = []
        def start(name, attrs) : 
            if name == "outline" and (\
                ((attrs.has_key("type") and\
                attrs["type"] in ["pie","rss"])) or\
                not attrs.has_key("type")):

                l.append((attrs["text"].encode("UTF-8"),attrs["xmlUrl"]))

        p = xml.parsers.expat.ParserCreate()
        p.StartElementHandler = start
        d = self.read_decode(filename)
        p.Parse(d, 1)
        return l

    @source
    def source_urls(self, filename, **kwargs):
        l = []
        f = open(filename, "r")
        d = f.read().split('\n')[:-1]
        f.close()

        for feed in d:
            l.append((None, feed))
        return l

    @source
    def source_url(self, URL, **kwargs):
        if kwargs.has_key("tag"):
            return [(kwargs["tag"], URL)]
        return [(None, URL)]

    # Key-binds for feed based filtering.
    def next_filter(self):
        if self.filter_idx < len(self.filterlist) - 1:
            self.filter_idx += 1
            return 1
        return 0

    def prev_filter(self):
        if self.filter_idx > 0:
            self.filter_idx -= 1
            return 1
        return 0

    def handler(self, handlers, path, **kwargs):
        if not "text" in kwargs:
            kwargs["text"] = False
        if not "fetch" in kwargs:
            kwargs["fetch"] = False
        if not "ext" in kwargs:
            kwargs["ext"] = None
        handlers.update(\
                {kwargs["ext"] : (path, kwargs["text"], kwargs["fetch"])})

    def image_handler(self, path, **kwargs):
        self.handler(self.handlers["image"], path, **kwargs)

    def link_handler(self, path, **kwargs):
        self.handler(self.handlers["browser"], path, **kwargs)

    def default_status(self):
        self.message("%8%B" + ("Canto %s.%s.%s " % VERSION_TUPLE) +\
                "%b%2" + " ".join([str(x) for x in self.key_handlers]) + "%0", 1)
