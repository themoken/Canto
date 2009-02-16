#!/bin/bash

pkill -INT -f "^python.*canto-fetch"
killall -INT canto

OLDPPATH=$PYTHONPATH
OLDMPATH=$MANPATH

python setup.py install --prefix=$PWD/root

PYVER=`python -c "import sys; print sys.version[:3]"`

if [ -e "$PWD/root/lib64" ]; then
    echo "Detected 64bit install"
    LIBDIR="lib64"
else
    LIBDIR="lib"
fi

export PYTHONPATH="$PWD/root/$LIBDIR/python$PYVER/site-packages:$OLDPPATH"
export MANPATH="$PWD/root/share/man:$OLDMPATH"

bin/canto-fetch -b
bin/canto

pkill -INT -f "^python.*canto-fetch"
export PYTHONPATH=$OLDPPATH
export MANPATH=$OLDMPATH
