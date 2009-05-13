/* Canto - ncurses RSS reader
   Copyright (C) 2008 Jack Miller <jack@codezen.org>

   This program is free software; you can redistribute it and/or modify
   it under the terms of the GNU General Public License version 2 as 
   published by the Free Software Foundation.*/

#include <Python.h>
#include <py_curses.h>

char *lstrip(char *s)
{
    int i = 0;
    for(i=0;s[i];i++) {
        if((s[i] != ' ')&&(s[i] != '\t'))
            break;
    }

    return &s[i];
}

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
            int bytes = mbtowc(dest, &message[i], 3) - 1;
            if (bytes >= 0) {
                int rwidth = wcwidth(dest[0]);
                if(rwidth < 0)
                    rwidth = 1;
                i += bytes;
                len += rwidth;
            } else {
                i++;
                len += 1;
            }
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

#define COLOR_MEMORY 8
static void style_box(WINDOW *win, char code)
{
    /* This function's limited memory */
    static int colors[COLOR_MEMORY] = {0};
    static int color_idx = 0;
    static char attrs[6] = {0,0,0,0,0,0};

    if (code == 'B') {
        attrs[0]++;
        if(!attrs[5])
            wattron(win, A_BOLD);
    }
    else if (code == 'b') {
        attrs[0]--;
        if(!attrs[0])
            wattroff(win, A_BOLD);
    }
    else if (code == 'U') {
        attrs[1]++;
        if(!attrs[5])  
            wattron(win, A_UNDERLINE);
    }
    else if (code == 'u') {
        attrs[1]--;
        if(!attrs[1])
            wattroff(win, A_UNDERLINE);
    }
    else if (code == 'S') {
        attrs[2]++;
        if(!attrs[5])
            wattron(win, A_STANDOUT);
    }
    else if (code == 's') {
        attrs[2]--;
        if(!attrs[2])
            wattroff(win, A_STANDOUT);
    }
    else if (code == 'R') {
        attrs[3]++;
        if(!attrs[5])
            wattron(win, A_REVERSE);
    }
    else if (code == 'r') {
        attrs[3]--;
        if(!attrs[3])
            wattroff(win, A_REVERSE);
    }
    else if (code == 'D') {
        attrs[4]++;
        if(!attrs[5])
            wattron(win, A_DIM);
    }
    else if (code == 'd') {
        attrs[4]--;
        if(!attrs[4])
            wattroff(win, A_DIM);
    }   
    /* For some reason wattron(win, A_NORMAL) doesn't work. */
    else if (code == 'N') {
        attrs[5]++;
        if (win)
            wattrset(win, 0);
    }
    else if (code == 'n') {
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
    else if (code == 'C') {
        int j = 0;
        for(j = 0; j < 5; j++)
            attrs[j] = 0;
        if (win)
            wattrset(win, 0);
    }
    else if (code == '0') {
        if ((color_idx != COLOR_MEMORY - 1)||(!colors[color_idx]))
            color_idx = (color_idx > 1) ? color_idx - 1: 1;
        colors[color_idx] = 0;
        wattron(win, COLOR_PAIR(colors[color_idx - 1]));
    }
    else if ((code >= '1') && (code <= '8')) {
        if (color_idx == COLOR_MEMORY - 1) {
            if (colors[color_idx]) {
                int i = 0;
                for (i = 0; i < color_idx; i++)
                    colors[i] = colors[i + 1];
            }
            colors[color_idx] = code - '0';
            wattron(win, COLOR_PAIR(colors[color_idx]));
        } 
        else {
            colors[color_idx] = code - '0';
            wattron(win, COLOR_PAIR(colors[color_idx]));
            color_idx++;
        }
    }
}

static int putxy(WINDOW *win, int width, int *i, int *y, int *x, char *str)
{
    if ((unsigned char) str[0] > 0x7F) {
        wchar_t dest[2];
        int bytes = mbtowc(dest, &str[0], 3) - 1;

        if (bytes >= 0) {
            /* To deal with non-latin characters that can take
               up more than one character's alotted width, 
               with offset x by wcwidth(character) rather than 1 */

            /* Took me forever to find that function, thanks
               Andreas (newsbeuter) for that one. */

            int rwidth = wcwidth(dest[0]);
            if (rwidth < 0)
                rwidth = 1;
            if (rwidth > (width - *x))
                return 1;

            dest[1] = 0;
            mvwaddwstr(win, *y, *x, dest);
            *x += rwidth;
            *i += bytes;
        }
    } else
        mvwaddch(win, *y, (*x)++, str[0]);

    return 0;
}

static int do_char(WINDOW *win, int width, int *i, int *y, int *x, char *str)
{
    if (!str[*i]) {
        return -1;
    } else if (str[*i] == '\\') {
        (*i)++;
        putxy(win, width, i, y, x, &str[*i]);
    } else if (str[*i] == '%') {
        (*i)++;
        if (!str[(*i)])
            return -1;
        else
            style_box(win, str[*i]);
    } else if (str[*i] == ' ') {
        int tmp = theme_strlen(&str[*i + 1], ' ');
        if ((tmp >= (width - *x)) && (tmp < width)) {
            (*i)++;
            return -2;
        }
        else
            putxy(win, width, i, y, x, &str[*i]);
    } else if(putxy(win, width, i, y, x, &str[*i]))
        return -2;

    return 0;
}

static PyObject * mvw(PyObject *self, PyObject *args)
{
    int y, x, width, rep_len, end_len, ret;
    char *message, *rep, *end;
    const char *m_enc, *r_enc, *e_enc;
    PyObject *window;
    WINDOW *win;

    /* We use the 'et' format because we don't want Python
       to touch the encoding and generate Unicode Exceptions */

    if(!PyArg_ParseTuple(args, "Oiiietetet", 
                &window, &y, &x, &width, &m_enc, &message,
                &r_enc, &rep, &e_enc, &end))
            return NULL;

    if (window != Py_None)
        win = ((PyCursesWindowObject *)window)->win;
    else
        win = NULL;
    
    rep_len = strlen(rep);
    end_len = theme_strlen(end, 0);

    /* Make width relative to current x */
    width += x;

    int i = 0;
    for (i = 0; ((x < width - end_len) || (message[i] == '%')); i++) {
        ret = do_char(win, width - end_len, &i, &y, &x, message);
        if (ret)
            break;
    }

    int j = 0;
    for(j = 0; x < (width - end_len); j = (j + 1) % rep_len)
        do_char(win, width - end_len, &j, &y, &x, rep);

    for(j = 0; end[j]; j++)
        do_char(win, width, &j, &y, &x, end);

    PyMem_Free(rep);
    PyMem_Free(end);

    if (ret == -1) {
        PyMem_Free(message);
        return Py_BuildValue("s", NULL);
    }
    else {
        PyObject *r = Py_BuildValue("s", lstrip(&message[i]));
        PyMem_Free(message);
        return r;
    }
}


static PyMethodDef MvWMethods[] = {
    {"core", mvw, METH_VARARGS, "Wide char print."},
    {"tlen", tlen, METH_VARARGS, "Len ignoring theme escapes, and accounting for Unicode character width."},
    {NULL, NULL, 0, NULL}
};

PyMODINIT_FUNC
initwidecurse()
{
    Py_InitModule("widecurse", MvWMethods);
}
