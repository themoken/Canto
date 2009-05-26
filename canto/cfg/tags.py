from canto.utility import Cycle, get_list_of_instances
from canto.tag import Tag

def register(c):
    c.tags = [None]
    c.cfgtags = []
    c.tag_filters = [None]
    c.tag_sorts = [[None]]
    
    def set_default_tag_filters(filters):
        c.tag_filters = get_list_of_instances(filters)

    def set_default_tag_sorts(sorts):
        c.tag_sorts = get_list_of_instances(sorts)

    def add_tag(tags, **kwargs):
        if "sorts" in kwargs:
            kwargs["sorts"] = \
                Cycle(get_list_of_instances(kwargs["sorts"]))
        else:
            kwargs["sorts"] = Cycle([[None]])

        if "filters" in kwargs:
            kwargs["filters"] = kwargs["filters"]
        else:
            kwargs["filters"] = c.tag_filters

        if not hasattr(tags, "__iter__"):
            tags = [tags]

        for t in tags:
            c.cfgtags.append(Tag(\
                    c,
                    c.default_renderer,
                    kwargs["sorts"],
                    kwargs["filters"],
                    unicode(t, "UTF-8", "ignore")))

    c.locals.update({
        "add_tag" : add_tag,
        "default_tag_sorts" : set_default_tag_sorts,
        "default_tag_filters" : set_default_tag_filters})

def post_parse(c):
    c.tags = c.locals["tags"]

def validate_tags(c):
    configured_tags = [ x.tag for x in c.cfgtags ]
    potential_tags = []

    if type(c.tags) != list:
        raise Exception, "tags must be a list of lists of strings"

    if not len(c.tags):
        raise Exception, "tags must not be empty"

    one_good_set = 0
    for i in c.tags:
        if i:
            if type(i) != list:
                raise Exception, "tags must be a list of lists of strings"
            if not len(i):
                continue
            one_good_set = 1
            for t in i:
                if type(t) not in [str, unicode]:
                    raise Exception, "tags are referenced as strings, not %s" %\
                        type(t)
                if type(t) == str:
                    t = unicode(t, "UTF-8", "ignore")
                if t not in potential_tags and\
                    t not in configured_tags:
                    potential_tags.append(t)
        elif i == None:
            # Default case
            one_good_set = 1

    if not one_good_set:
        raise Exception, "tag lists must not all be empty"

    for f in c.feeds:
        for t in f.tags:
            if type(t) not in [str, unicode]:
                raise Exception, "tags are referenced as strings, not %s" %\
                        type(t)
            if type(t) == str:
                t = unicode(t, "UTF-8", "ignore")
            if t not in configured_tags and\
                t not in potential_tags:
                potential_tags.append(t)

    for tag in potential_tags:
        c.cfgtags.append(Tag(c, c.default_renderer,\
                Cycle(c.tag_sorts), c.tag_filters, tag))

    def get_tag_obj(s):
        for t in c.cfgtags:
            if t.tag == s:
                return t

    newtags = []
    for tagl in c.tags:
        new = []
        if tagl == None:
            for f in c.feeds:
                obj = get_tag_obj(f.tags[0])
                if obj not in new:
                    new.append(obj)
        else:
            for x in tagl:
                obj = get_tag_obj(unicode(x, "UTF-8", "ignore"))
                if obj not in new:
                    new.append(obj)
        newtags.append(new)

    return newtags

def validate(c):
    c.tags = Cycle(validate_tags(c))

class StubFeed:
    def __init__(self, tags):
        self.tags = tags

def test(c):
    c.feeds = []
    c.cfgtags = []

    #Bullshit type for tags
    for badtype in [None, [], ["garbage"], [[1]], [[]]]:
        c.tags = badtype
        try:
            validate_tags(c)
        except:
            pass
        else:
            raise Exception,\
                "Bad tags (%s) failed to raise exception." % badtype

    # Actually creating a tag requires some stub defaults
    c.default_renderer = None
    c.tag_sorts = []
    c.tag_filters = []

    #Default
    c.tags = [["sometag"]]
    validate_tags(c)
    if "sometag" not in [t.tag for t in c.cfgtags]:
        raise Exception, "Failed to use hard coded tag."
    
    # Stub feeds to create tags for.
    c.feeds = [StubFeed([u"Slashdot",u"news"]), StubFeed([u"Reddit", u"news"])]
    c.tags = [None]

    c.tags = validate_tags(c)
    for tag in [u"Slashdot", u"Reddit", u"news"]:
        if tag not in [t.tag for t in c.cfgtags]:
            raise Exception, "Failed to use feed tag."
    tagstr = [t.tag for t in c.tags[0]]
    if tagstr != [u"Slashdot", u"Reddit"]:
        raise Exception, "Failed to generate default tags %s" % tagstr

    print "Tag tests passed."
