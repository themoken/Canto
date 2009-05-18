from canto.utility import Cycle

def filter_dec(c, f):
    if not f:
        return None

    class fdec():
        def __init__(self, instance, log):
            self.instance = instance()
            self.log = log

        def __str__(self):
            return self.instance.__str__()

        def __call__(self, *args):
            try:
                return self.instance(*args)
            except:
                self.log("\nException in filter:")
                self.log("%s" % traceback.format_exc())
    return fdec(f, c.log)

def register(c):
    c.tag_filters = [None]
    c.filters = [None]

    c.locals.update({
        "tag_filters" : c.tag_filters,
        "filters" : c.filters })

def post_parse(c):
    c.tag_filters = [filter_dec(c, x) for x in c.locals["tag_filters"]]
    c.filters = Cycle([filter_dec(c, x) for x in c.locals["filters"]])

def validate(c):
    pass
