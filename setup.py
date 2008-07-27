#!/usr/bin/python

from distutils.core import setup, Extension
from distutils.command.install_data import install_data
import os

version = ['0','4','3']
man_date = "17 July 2008"

class Canto_install_data(install_data):
    def run(self):
        ret = install_data.run(self)

        install_cmd = self.get_finalized_command('install')
        libdir = install_cmd.install_lib
        mandir = install_cmd.install_data + "/share/man/man1/"

        os.system("sed -ie 's/VERSION_TUPLE/\(" + ",".join(version) + "\)/g' " + libdir + "/canto/canto.py")
        os.system("sed -ie 's/VERSION_TUPLE/\(" + ",".join(version) + "\)/g' " + libdir + "/canto_fetch/canto_fetch.py")
        os.system("sed -ie 's/MAN_VERSION/" + ".".join(version) + "/g' " + mandir + "canto.1")
        os.system("sed -ie 's/MAN_DATE/" + man_date + "/g' " + mandir + "canto.1")

        os.system("sed -ie 's/SETUPPY_SET_MAN_PATH/\"" + install_cmd.install_data.replace('/', '\\/') + "\\/share\\/man\\/man1\"/g' " + libdir + "/canto/cfg.py")
        os.system("sed -ie 's/SETUPPY_SET_BIN_PATH/\"" + install_cmd.install_scripts.replace('/', '\\/') + "\"/g' " + libdir + "/canto/cfg.py")

setup(name='Canto',
        version=".".join(version),
        description='An ncurses RSS aggregator.',
        author='Jack Miller',
        author_email='jack@codezen.org',
        url='http://codezen.org/canto',
        license='GPLv2',
        scripts=['bin/canto','bin/canto-fetch'],
        packages=['canto','canto_fetch'],
        ext_modules=[Extension('canto.widecurse', sources = ['canto/widecurse.c'], libraries = ['ncursesw'])],
        data_files = [("share/man/man1/", ["man/canto.1"])],
        cmdclass={'install_data': Canto_install_data}
)
