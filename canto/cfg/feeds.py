from canto.feed import Feed

def register(c):
    c.feeds = []
    c.default_rate = 5
    c.default_keep = 40
    c.default_filter = None
    c.default_sort = None
    
    def add(URL, **kwargs):
        if (not URL) or URL == "":
            return -1

        for key in ["keep","rate"]:
            if not key in kwargs:
                kwargs[key] = getattr(c, "default_" + key)

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

        # The tag is the only thing that has to be unique, so we ignore
        # any duplicate URLs, or everything  will break.

        if not URL in [f.URL for f in c.feeds]:
            c.feeds.append(Feed(c, c.feed_dir +\
                    URL.replace("/", " "), URL,
                    kwargs["tags"],
                    kwargs["rate"],
                    kwargs["keep"],
                    kwargs["filter"],
                    kwargs["username"],
                    kwargs["password"]))

    def change_feed(URL, **kwargs):
        l = [f for f in c.feeds if f.URL == URL]
        if not len(l):
            return

        feed = l[0]
        for key in ["keep","rate","renderer","filter","username","password"]:
            if key in kwargs:
                setattr(feed, key, kwargs[key])

    def set_default_rate(rate):
        c.default_rate = rate

    def set_default_keep(keep):
        c.default_keep = keep

    c.locals.update({
        "add" : add,
        "change_feed" : change_feed,
        "default_rate" : set_default_rate,
        "default_keep" : set_default_keep})

def post_parse(c):
    pass

def validate(c):
    pass

def test(c):
    pass
