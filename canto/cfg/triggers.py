def register(c):
    c.triggers = ["interval","signal"]
    c.locals.update({"triggers" : c.triggers})

def post_parse(c):
    c.triggers = c.locals["triggers"]

def validate(c):
    for t in c.triggers:
        if t not in ["interval","signal","change_tag"]:
            raise Exception, "%s is not a valid trigger name, try\
                    \"interval\", \"signal\", or \"change_tag\""

def test(c):
    pass
