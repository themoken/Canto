#!/bin/bash

killall -9 canto-fetch
killall -9 canto

OLDPPATH=$PYTHONPATH
OLDMPATH=$MANPATH

python setup.py install --prefix=$PWD/root

PYVER=`python -c "import sys; print sys.version[:3]"`

export PYTHONPATH="$PWD/root/lib/python$PYVER/site-packages:$OLDPPATH"
export MANPATH="$PWD/root/share/man:$OLDMPATH"

bin/canto-fetch -b
bin/canto -u

export PYTHONPATH=$OLDPPATH
export MANPATH=$OLDMPATH
