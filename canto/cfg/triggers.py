def register(c):
    c.triggers = ["interval","signal"]
    c.locals.update({"triggers" : c.triggers})

def post_parse(c):
    c.triggers = c.locals["triggers"]

def validate(c):
    pass

def test(c):
    pass
