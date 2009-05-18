def register(c):
    c.handlers = {
        "link" : {},
        "image" : {}
    }

    def handler(handlers, path, **kwargs):
        if not "text" in kwargs:
            kwargs["text"] = False
        if not "fetch" in kwargs:
            kwargs["fetch"] = False
        if not "ext" in kwargs:
            kwargs["ext"] = None
        handlers.update(\
                {kwargs["ext"] : (path, kwargs["text"], kwargs["fetch"])})

    def image_handler(path, **kwargs):
        handler(c.handlers["image"], path, **kwargs)

    def link_handler(path, **kwargs):
        handler(c.handlers["link"], path, **kwargs)

    c.locals.update({
        "link_handler": link_handler,
        "image_handler": image_handler})

def post_parse(c):
    pass

def validate(c):
    pass
