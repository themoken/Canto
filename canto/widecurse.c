#include <Python.h>
#include <py_curses.h>
#include <ncursesw/ncurses.h>

static int theme_strlen(char *message, char end)
{
    int len = 0;
    int i = 0;

    while ((message[i] != end) && (message[i] != 0)) {
        if (message[i] == '%') {
            i++;
        } else if (message[i] == '\\') {
            i++;
            len++;
        } else if ((unsigned char) message[i] > 0x7f) {
            wchar_t dest[2];
            i += mbtowc(dest, &message[i], 3) - 1;
            len += wcwidth(dest[0]);
        } else if (message[i] != '\n')
            len++;
        i++;
    }

    return len;
}

static PyObject *tlen(PyObject *self, PyObject *args)
{
    char *message;
    char end = 0;

    if(!PyArg_ParseTuple(args, "s|c", &message, &end))
            return NULL;

    return Py_BuildValue("i",theme_strlen(message, end));
}

static PyObject * mvw(PyObject *self, PyObject *args)
{
    int y, x, width, wrap;
    char *message;
    PyObject *window;
    WINDOW *win;

    if(!PyArg_ParseTuple(args, "Oiiiis", 
                &window, &y, &x, &width, &wrap, &message))
            return NULL;

    if (window != Py_None)
        win = ((PyCursesWindowObject *)window)->win;
    else
        win = NULL;

    /* This function's limited memory */
    static int cur_colp = 1;
    static int prev_colp = 1;
    static char attrs[6] = {0,0,0,0,0,0};
    int i = 0;

    for (i = 0; i <= width; i++) {
        if (!message[i]) {
            return Py_BuildValue("si", NULL, x);
        } else if (message[i] == '\n') {
            wmove(win, y, x);
            wclrtoeol(win);
            i++;
            break;
        } else if (message[i] == '\\') {
            i++;
            width++;
            mvwaddch(win, y, x++, message[i]);
        } else if (message[i] == '%') {
            width += 2;
            i++;
            if (!message[i])
                return Py_BuildValue("si", NULL, x);
            else if (message[i] == 'B') {
                attrs[0]++;
                if(!attrs[5])
                    wattron(win, A_BOLD);
            }
            else if (message[i] == 'b') {
                attrs[0]--;
                if(!attrs[0])
                    wattroff(win, A_BOLD);
            }
            else if (message[i] == 'U') {
                attrs[1]++;
                if(!attrs[5])  
                    wattron(win, A_UNDERLINE);
            }
            else if (message[i] == 'u') {
                attrs[1]--;
                if(!attrs[1])
                    wattroff(win, A_UNDERLINE);
            }
            else if (message[i] == 'S') {
                attrs[2]++;
                if(!attrs[5])
                    wattron(win, A_STANDOUT);
            }
            else if (message[i] == 's') {
                attrs[2]--;
                if(!attrs[2])
                    wattroff(win, A_STANDOUT);
            }
            else if (message[i] == 'R') {
                attrs[3]++;
                if(!attrs[5])
                    wattron(win, A_REVERSE);
            }
            else if (message[i] == 'r') {
                attrs[3]--;
                if(!attrs[3])
                    wattroff(win, A_REVERSE);
            }
            else if (message[i] == 'D') {
                attrs[4]++;
                if(!attrs[5])
                    wattron(win, A_DIM);
            }
            else if (message[i] == 'd') {
                attrs[4]--;
                if(!attrs[4])
                    wattroff(win, A_DIM);
            }   
            /* For some reason wattron(win, A_NORMAL) doesn't work. */
            else if (message[i] == 'N') {
                attrs[5]++;
                if (win)
                    wattrset(win, 0);
            }
            else if (message[i] == 'n') {
                attrs[5]--;
                if(!attrs[5]) {
                    if(attrs[0])
                        wattron(win, A_BOLD);
                    if(attrs[1])
                        wattron(win, A_UNDERLINE);
                    if(attrs[2])
                        wattron(win, A_STANDOUT);
                    if(attrs[3])
                        wattron(win, A_REVERSE);
                    if(attrs[4])
                        wattron(win, A_DIM);
                }
            }
            else if (message[i] == 'C') {
                int j = 0;
                for(j = 0; j < 5; j++)
                    attrs[j] = 0;
                if (win)
                    wattrset(win, 0);
            }
            else if (message[i] == '0') {
                cur_colp = prev_colp;
                wattron(win, COLOR_PAIR(cur_colp));
            }
            else if ((message[i] >= '1') && (message[i] <= '8')) {
                prev_colp = cur_colp;
                cur_colp = message[i] - '0';
                wattron(win, COLOR_PAIR(cur_colp));
            }
            /* Handle printing unicode */
        } else if ((unsigned char) message[i] > 0x7F) {
            int bytes = 0;
            wchar_t dest[2];
            bytes = mbtowc(dest, &message[i], 3) - 1;
            if (bytes < 0)
                mvwaddch(win, y, x++, message[i]);
            else {
                /* To deal with non-latin characters that can take
                   up more than one character's alotted width, 
                   with offset x by wcwidth(character) rather than 1 */

                /* Took me forever to find that function, thanks
                   Andreas (newsbeuter) for that one. */

                int rwidth = wcwidth(dest[0]);
                if (rwidth > (width - i))
                    break;

                dest[1] = 0;
                mvwaddwstr(win, y, x, dest);
                x += rwidth;

                /* Move to the next character and kludge the width
                   to keep the for loop correct. */
                i += bytes;
                width += (bytes - (rwidth - 1));
            }
        } else
            mvwaddch(win, y, x++, message[i]);

        /* Handle intelligent wrapping on words by ensuring
           that the next word can fit, or bail on the line. */

        if ((wrap)&&(message[i] == ' ')) {
            int tmp = theme_strlen(&message[i + 1], ' ');
            if ((tmp >= (width - i)) && (tmp < width)) {
                i++;
                break;
            }
        }
    }

    return Py_BuildValue("si", &message[i], x);
}


static PyMethodDef MvWMethods[] = {
    {"core", mvw, METH_VARARGS, "Wide char print."},
    {"tlen", tlen, METH_VARARGS, "Len ignoring theme escpaes, and accounting for Unicode character width."},
    {NULL, NULL, 0, NULL}
};

PyMODINIT_FUNC
initwidecurse()
{
    Py_InitModule("widecurse", MvWMethods);
}
