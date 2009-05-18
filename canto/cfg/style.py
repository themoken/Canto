from canto.interface_draw import Renderer

def register(c):
    c.colors = [("white","black"),("blue","black"),("yellow","black"),\
        ("green","black"),("pink","black"),("black","black"),\
        ("blue","black"),(0,0)]

    c.default_renderer = Renderer()
    c.default_msg_tick = 5
    
    def set_default_renderer(renderer):
        c.default_renderer = renderer

    def get_default_renderer():
        return c.default_renderer

    c.locals.update({
        "colors" : c.colors,
        "renderer" : Renderer,
        "default_renderer" : set_default_renderer,
        "get_default_renderer" : get_default_renderer})

def post_parse(c):
    pass

def validate(c):
    pass
