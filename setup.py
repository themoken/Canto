#!/usr/bin/python

from distutils.core import setup, Extension
from distutils.command.install_data import install_data
import os

class Canto_install_data(install_data):
    def run(self):
        ret = install_data.run(self)

        install_cmd = self.get_finalized_command('install')
        libdir = install_cmd.install_lib
        os.system("sed -ie 's/SETUPPY_SET_MAN_PATH/\"" + install_cmd.install_data.replace('/', '\\/') + "\\/share\\/man\\/man1\"/g' " + libdir + "/canto/cfg.py")
        os.system("sed -ie 's/SETUPPY_SET_BIN_PATH/\"" + install_cmd.install_scripts.replace('/', '\\/') + "\"/g' " + libdir + "/canto/cfg.py")

setup(name='Canto',
        version='0.4.0',
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
