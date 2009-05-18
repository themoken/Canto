def hook_dec(c, fn):
    if not fn:
        return None

    def hdec(*args):
        try:
            r = fn(*args)
        except:
            c.log("\nException in hook:")
            c.log("%s" % traceback.format_exc())
            return 0
        return r
    return hdec

def register(c):
    c.resize_hook = None
    c.new_hook = None
    c.select_hook = None
    c.unselect_hook = None
    c.start_hook = None
    c.end_hook = None
    c.update_hook = None
    c.state_change_hook = None

    c.locals.update({
        "resize_hook" : c.resize_hook,
        "new_hook" : c.new_hook,
        "select_hook" : c.select_hook,
        "unselect_hook" : c.unselect_hook,
        "start_hook" : c.start_hook,
        "end_hook" : c.end_hook,
        "update_hook" : c.update_hook,
        "state_change_hook" : c.state_change_hook})

def post_parse(c):
    for hook in ["resize_hook","new_hook","select_hook","update_hook",\
            "unselect_hook","start_hook","end_hook", "state_change_hook"]:
        setattr(c, hook, hook_dec(c, c.locals[hook]))

def validate(c):
    pass
