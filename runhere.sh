#!/bin/bash

killall -9 canto-fetch
killall -9 canto

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

export PYTHONPATH=$OLDPPATH
export MANPATH=$OLDMPATH
