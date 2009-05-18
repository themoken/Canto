from canto.const import VERSION_TUPLE

def default_status(c):
    return u"%8%B" + u"Canto %d.%d.%d" % VERSION_TUPLE + u"%b%1"

def register(c):
    c.columns = 1
    c.height = 0
    c.width = 0

    c.reader_lines = 0
    c.reader_orientation = None

    c.gui_top = 0
    c.gui_right = 0
    c.gui_height = 0
    c.gui_width = 0

    c.status = default_status

    c.locals.update({
        "status" : c.status,
        "reader_orientation" : c.reader_orientation,
        "reader_lines" : c.reader_lines,
        "columns" : c.columns})

def post_parse(c):
    for attr in ["columns", "reader_orientation","reader_lines", "status"]:
        setattr(c, attr, c.locals[attr])

def validate(c):
    pass

def test(c):
    pass
