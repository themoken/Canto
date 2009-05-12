# -*- coding: utf-8 -*-

#Canto - ncurses RSS reader
#   Copyright (C) 2008 Jack Miller <jack@codezen.org>
#
#   This program is free software; you can redistribute it and/or modify
#   it under the terms of the GNU General Public License version 2 as 
#   published by the Free Software Foundation.

from const import VERSION_TUPLE
from utility import Cycle
import interface_draw
import utility
import feed
import tag

import xml.parsers.expat
import traceback
import chardet
import codecs
import os

class Cfg:
    def __init__(self, conf, log_file, feed_dir, script_dir):
        self.handlers = {
            "link" : {},
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
                         ";" : "goto_reltag",
                         ":" : "goto_tag",
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
                              " " : "quit"}

        self.colors = [("white","black"),("blue","black"),("yellow","black"),
                ("green","black"),("pink","black"),("black","black"),("blue","black"),(0,0)]

        self.feeds = []
        self.tags = [None]
        self.cfgtags = []

        self.default_rate = 5
        self.default_keep = 40
        self.default_filter = None
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

        self.status = default_status

        self.reader_lines = 0
        self.reader_orientation = None

        self.resize_hook = None
        self.new_hook = None
        self.select_hook = None
        self.unselect_hook = None
        self.start_hook = None
        self.end_hook = None
        self.update_hook = None

        self.tag_filters = [None]
        self.tag_sorts = [[None]]
        self.filters = [None]

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
            f.write("""add("""\
                    """"http://rss.slashdot.org/slashdot/Slashdot")\n""")
            f.write("""add("""\
                    """"http://reddit.com/.rss")\n""")
            f.write("""add("""\
                    """"http://kerneltrap.org/node/feed")\n""")
            f.write("""add("""\
                    """"http://codezen.org/canto/feeds/latest")\n""")
            f.write("\n")
            f.close()
            self.no_conf = 1

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

    def wrap_args(self, kwargs):
        for attr in ["renderer", "filter"]:
            if attr in kwargs:
                kwargs[attr] = utility.get_instance(kwargs[attr])
        if "filter" in kwargs:
            kwargs["filter"] = self.filter_dec(kwargs["filter"])

        return kwargs

    def addfeed(self, tag, URL, **kwargs):
        print "'add_feed' is deprecated! Update to new 'add' syntax."
        print "See codezen.org/canto for instructions."
        kwargs["tags"] = [tag]
        self.add(URL, **kwargs)

    def add(self, URL, **kwargs):
        if (not URL) or URL == "":
            return -1

        for key in ["keep","rate","renderer"]:
            if not key in kwargs:
                kwargs[key] = getattr(self, "default_" + key)

        for key in ["username","password", "filter"]:
            if not key in kwargs:
                kwargs[key] = None

        if not "tags" in kwargs:
            kwargs["tags"] = [None]
        else:
            tgs = []
            for tag in kwargs["tags"]:
                if tag:
                    if type(tag) != unicode:
                        tgs.append(unicode(tag, "UTF-8", "ignore"))
                    else:
                        tgs.append(tag)
                else:
                    tgs.append(None)
            kwargs["tags"] = tgs

        kwargs = self.wrap_args(kwargs)

        # The tag is the only thing that has to be unique, so we ignore
        # any duplicate URLs, or everything  will break.

        if not URL in [f.URL for f in self.feeds]:
            self.feeds.append(feed.Feed(self, self.feed_dir +\
                    URL.replace("/", " "), URL,
                    kwargs["tags"],
                    kwargs["rate"],
                    kwargs["keep"],
                    kwargs["renderer"],
                    kwargs["filter"],
                    kwargs["username"],
                    kwargs["password"]))
            return 1
        return -1

    def set_default_rate(self, rate):
        self.default_rate = rate

    def set_default_keep(self, keep):
        self.default_keep = keep

    def set_default_renderer(self, renderer):
        self.default_renderer = renderer

    def set_default_tag_filters(self, filters):
        self.tag_filters = utility.get_list_of_instances(filters)

    def set_default_tag_sorts(self, sorts):
        self.tag_sorts = utility.get_list_of_instances(sorts)

    def change_feed(self, URL, **kwargs):
        l = [f for f in self.feeds if f.URL == URL]
        if not len(l):
            return

        kwargs = self.wrap_args(kwargs)

        feed = l[0]
        for key in ["keep","rate","renderer","filter","username","password"]:
            if key in kwargs:
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

    def read_decode(self, filename, top_encode=0):
        enc = "utf-8"

        try:
            f = open(filename, "r")
            data = f.read()

            try:
                ret = unicode(data, enc)
            except UnicodeDecodeError:
                # If the Python built-in decoders can't figure it
                # out, it might need some help from chardet.
                enc = chardet.detect(data)["encoding"]
                ret = unicode(data, enc)
                self.log("Chardet detected encoding %s for %s" %\
                        (enc,filename))
        except :
            self.log("Failed to open config! (%s)" % sys.exc_info())
        finally:
            f.close()

        if top_encode and not ret.startswith("# -*- coding:"):
            ret = "# -*- coding: " + enc + " -*-\n" + ret

        return ret

    def parse(self, data = None):

        locals = {"addfeed":self.addfeed,
            "add_feed": self.addfeed,
            "add": self.add,
            "add_tag" : self.add_tag,
            "tags" : self.tags,
            "change_feed": self.change_feed,
            "default_rate" : self.set_default_rate,
            "default_keep" : self.set_default_keep,
            "default_renderer" : self.set_default_renderer,
            "default_tag_filters" : self.set_default_tag_filters,
            "default_tag_sorts" : self.set_default_tag_sorts,
            "renderer" : interface_draw.Renderer,
            "status" : self.status,
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

        if not data:
            data = self.read_decode(self.path, 1)

        try :
            exec(data.encode("UTF-8"), {}, locals)
        except :
            print "Invalid line in config."
            traceback.print_exc()
            raise

        # exec cannot modify basic type
        # locals directly, so we do it by hand.

        for attr in ["render", "columns", "reader_orientation",\
                "reader_lines", "status", "tags"]:
            if attr in locals:
                setattr(self, attr, locals[attr])

        for attr in ["filters"]:
            if attr in locals:
                setattr(self, attr, \
                        utility.get_list_of_instances(locals[attr]))

        # Deprecated attributes... will be eliminated > 0.6.0

        for attr in ["browser","text_browser"]:
            if attr in locals:
                print "Use of %s is deprecated! Use link_handler() instead." %\
                    attr
                if attr == "browser":
                    self.handlers["link"][None] = (locals[attr], 0, 0)
                elif attr == "text_browser":
                    self.handlers["link"][None] =\
                            (self.handlers["link"][None][0], 1, 0)

        # Wrap hooks in the exception handler
        for hook in ["resize_hook","new_hook","select_hook","update_hook",\
                "unselect_hook","start_hook","end_hook"]:
            if hook in locals:
                setattr(self, hook, self.hook_dec(locals[hook]))

        # Wrap filters in exception handler
        self.filters = Cycle([self.filter_dec(x) for x in self.filters])
        self.tag_filters = [self.filter_dec(x) for x in self.tag_filters]

        # Ensure we have at least one column
        if not self.columns:
            self.log("columns <1, set to 1")
            self.columns = 1

        # Convert all of the C-M-blah (human readable) keys into
        # key tuples used in the main loop.

        self.key_list = utility.conv_key_list(self.key_list)
        self.reader_key_list = utility.conv_key_list(self.reader_key_list)

    def source(fn):
        def source_dec(self, *args, **kwargs):
            append = False
            if "append" in kwargs:
                append = kwargs["append"]
                file = codecs.open(self.path, "a", "UTF-8")

            l = fn(self, *args, **kwargs)

            for f in l:
                if self.add(f[0], tags=[f[1]]) and append:
                    if f[1]:
                        file.write(u"""add("%s", tags=["%s"])\n""" % f)
                    else:
                        file.write(u"""add("%s")\n""" % f[0])

            if append:
                file.close()
        return source_dec
   
    @source
    def source_opml(self, filename, **kwargs):
        l = []
        def start(name, attrs) : 
            if name == "outline" and (\
                (("type" in attrs and\
                attrs["type"] in ["pie","rss"])) or\
                not ("type" in attrs)):

                if "xmlUrl" in attrs:
                    if "text" in attrs:
                        l.append((attrs["xmlUrl"], attrs["text"]))
                    else:
                        l.append((attrs["xmlUrl"], None))

        p = xml.parsers.expat.ParserCreate()
        p.StartElementHandler = start
        d = self.read_decode(filename)
        p.Parse(d.encode("UTF-8"), 1)
        return l

    @source
    def source_urls(self, filename, **kwargs):
        l = []
        d = self.read_decode(filename).split('\n')[:-1]
        for feed in d:
            l.append((feed, None))
        return l

    @source
    def source_url(self, URL, **kwargs):
        if "tag" in kwargs:
            return [(URL, kwargs["tag"])]
        return [(None, URL)]

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
        self.handler(self.handlers["link"], path, **kwargs)

    def add_tag(self, tags, **kwargs):
        if "sorts" in kwargs:
            kwargs["sorts"] = \
                Cycle(utility.get_list_of_instances(kwargs["sorts"]))
        else:
            kwargs["sorts"] = Cycle([[None]])

        if "filters" in kwargs:
            kwargs["filters"] = \
                    Cycle(utility.get_list_of_instances(kwargs["filters"]))
        else:
            kwargs["filters"] = Cycle(self.tag_filters)

        if not hasattr(tag, "__iter__"):
            tags = [tags]

        for t in tags:
            self.cfgtags.append(tag.Tag(\
                    self,
                    kwargs["sorts"],
                    kwargs["filters"],
                    unicode(t, "UTF-8", "ignore")))

    def get_real_tagl(self, tl):
        if not tl:
            tl = [ f.tags[0] for f in self.feeds ]
        if not hasattr(tl, "__iter__"):
            tl = [tl]

        r = []
        for t in tl:
            if t and type(t) != unicode:
                t = unicode(t, "UTF-8", "ignore")
            newtag = tag.Tag(self, Cycle(self.tag_sorts),\
                    Cycle(self.tag_filters), t)

            if newtag in self.cfgtags:
                newtag = self.cfgtags[self.cfgtags.index(newtag)]
            r.append(newtag)

        return r

    def validate_tags(self):
        # Change tags into actual tag objects
        self.tags = Cycle([ self.get_real_tagl(x) for x in self.tags ])

def default_status(cfg):
    return u"%8%B" + u"Canto %d.%d.%d" % VERSION_TUPLE + u"%b%1"
