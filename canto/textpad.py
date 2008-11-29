"""Simple textbox editing widget with Emacs-like keybindings."""

import curses.ascii as ascii
import curses

class Textbox:
    """Editing widget using the interior of a window object.
     Supports the following Emacs-like key bindings:

    Ctrl-A      Go to left edge of window.
    Ctrl-B      Cursor left, wrapping to previous line if appropriate.
    Ctrl-D      Delete character under cursor.
    Ctrl-E      Go to right edge (stripspaces off) or end of line (stripspaces on).
    Ctrl-F      Cursor right, wrapping to next line when appropriate.
    Ctrl-G      Terminate, returning the window contents.
    Ctrl-H      Delete character backward.
    Ctrl-J      Terminate if the window is 1 line, otherwise insert newline.
    Ctrl-K      If line is blank, delete it, otherwise clear to end of line.
    Ctrl-L      Refresh screen.
    Ctrl-N      Cursor down; move down one line.
    Ctrl-O      Insert a blank line at cursor location.
    Ctrl-P      Cursor up; move up one line.

    Move operations do nothing if the cursor is at an edge where the movement
    is not possible.  The following synonyms are supported where possible:

    KEY_LEFT = Ctrl-B, KEY_RIGHT = Ctrl-F, KEY_UP = Ctrl-P, KEY_DOWN = Ctrl-N
    KEY_BACKSPACE = Ctrl-h
    """
    def __init__(self, win):
        self.win = win
        (self.maxy, self.maxx) = win.getmaxyx()
        self.maxy = self.maxy - 1
        self.maxx = self.maxx - 1
        self.minx = win.getyx()[1]

        self.result = ""

        self.stripspaces = 1
        self.lastcmd = None
        win.keypad(1)

    def _end_of_line(self, y):
        "Go to the location of the first blank on the given line."
        last = self.maxx
        while 1:
            if ascii.ascii(self.win.inch(y, last)) != ascii.SP:
                last = min(self.maxx, last+1)
                break
            elif last == 0:
                break
            last = last - 1
        return last

    def do_command(self, ch):
        "Process a single editing command."
        (y, x) = self.win.getyx()
        self.lastcmd = ch
        if ch == ascii.SOH:                           # ^a
            self.win.move(y, 0)
        elif ch in (ascii.STX,curses.KEY_LEFT, ascii.BS,curses.KEY_BACKSPACE):
            if x > self.minx:
                self.win.move(y, x-1)
            elif y == 0:
                pass
            elif self.stripspaces:
                self.win.move(y-1, self._end_of_line(y-1))
            else:
                self.win.move(y-1, self.maxx)
            if ch in (ascii.BS, curses.KEY_BACKSPACE)\
                    and x > self.minx:
                self.win.delch()
        elif ch == ascii.EOT:                           # ^d
            self.win.delch()
        elif ch == ascii.ENQ:                           # ^e
            if self.stripspaces:
                self.win.move(y, self._end_of_line(y))
            else:
                self.win.move(y, self.maxx)
        elif ch in (ascii.ACK, curses.KEY_RIGHT):       # ^f
            if x < self.maxx:
                self.win.move(y, x+1)
            elif y == self.maxy:
                pass
            else:
                self.win.move(y+1, 0)
        elif ch == ascii.BEL:                           # ^g
            return 0
        elif ch == ascii.NL:                            # ^j
            if self.maxy == 0:
                return 0
            elif y < self.maxy:
                self.win.move(y+1, 0)
        elif ch == ascii.VT:                            # ^k
            if x == 0 and self._end_of_line(y) == 0:
                self.win.deleteln()
            else:
                # first undo the effect of self._end_of_line
                self.win.move(y, x)
                self.win.clrtoeol()
        elif ch == ascii.FF:                            # ^l
            self.win.refresh()
        elif ch in (ascii.SO, curses.KEY_DOWN):         # ^n
            if y < self.maxy:
                self.win.move(y+1, x)
                if x > self._end_of_line(y+1):
                    self.win.move(y+1, self._end_of_line(y+1))
        elif ch == ascii.SI:                            # ^o
            self.win.insertln()
        elif ch in (ascii.DLE, curses.KEY_UP):          # ^p
            if y > 0:
                self.win.move(y-1, x)
                if x > self._end_of_line(y-1):
                    self.win.move(y-1, self._end_of_line(y-1))
        elif ch > 0 and (y < self.maxy or x < self.maxx):
            # The try-catch ignores the error we trigger from some curses
            # versions by trying to write into the lowest-rightmost spot
            # in the window.
            try:
                self.win.addch(ch)
            except curses.error:
                pass

            self.result += unichr(ch)

        return 1

    def edit(self):
        "Edit in the widget window and collect the results."
        while 1:
            ch = self.win.getch()
            if not ch:
                continue
            if not self.do_command(ch):
                break
            self.win.refresh()
        return self.result
