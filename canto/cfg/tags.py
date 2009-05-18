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
            kwargs["filters"] = \
                    Cycle(get_list_of_instances(kwargs["filters"]))
        else:
            kwargs["filters"] = Cycle(c.tag_filters)

        if not hasattr(tags, "__iter__"):
            tags = [tags]

        for t in tags:
            c.cfgtags.append(Tag(\
                    c,
                    c.default_renderer,
                    kwargs["sorts"],
                    kwargs["filters"],
                    unicode(t, "UTF-8", "ignore")))

    def get_real_tagl(tl):
        if not tl:
            tl = [ f.tags[0] for f in c.feeds ]
        if not hasattr(tl, "__iter__"):
            tl = [tl]

        r = []
        for t in tl:
            if t and type(t) != unicode:
                t = unicode(t, "UTF-8", "ignore")
            newtag = Tag(c, c.default_renderer,
                    Cycle(c.tag_sorts), Cycle(c.tag_filters), t)

            if newtag in c.cfgtags:
                newtag = c.cfgtags[c.cfgtags.index(newtag)]
            if not newtag in r:
                r.append(newtag)
        return r

    def validate_tags():
        # Change tags into actual tag objects
        c.tags = Cycle([get_real_tagl(t) for t in c.tags])
    c.validate_tags = validate_tags

    c.locals.update({
        "add_tag" : add_tag,
        "default_tag_sorts" : set_default_tag_sorts,
        "default_tag_filters" : set_default_tag_filters})

def post_parse(c):
    c.tags = c.locals["tags"]

def validate(c):
    pass
