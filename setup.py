#!/usr/bin/python

from distutils.core import setup, Extension
from distutils.command.install_data import install_data
import os

version = ['0','5','0']
man_date = "16 September 2008"

class Canto_install_data(install_data):
    def run(self):
        ret = install_data.run(self)

        install_cmd = self.get_finalized_command('install')
        libdir = install_cmd.install_lib
        mandir = install_cmd.install_data + "/share/man/man1/"

        for f in ["/canto/canto.py","/canto/canto_fetch.py"]:
            os.system("sed -i 's/VERSION_TUPLE/\(" + ",".join(version) + "\)/g' " + libdir + f)

        for m in ["canto.1","canto-fetch.1"]:
            os.system("sed -i 's/MAN_VERSION/" + ".".join(version) + "/g' " + mandir + m)
            os.system("sed -i 's/MAN_DATE/" + man_date + "/g' " + mandir + m)

setup(name='Canto',
        version=".".join(version),
        description='An ncurses RSS aggregator.',
        author='Jack Miller',
        author_email='jack@codezen.org',
        url='http://codezen.org/canto',
        license='GPLv2',
        scripts=['bin/canto','bin/canto-fetch'],
        packages=['canto'],
        ext_modules=[Extension('canto.widecurse', sources = ['canto/widecurse.c'], libraries = ['ncursesw'])],
        data_files = [("share/man/man1/", ["man/canto.1", "man/canto-fetch.1"])],
        cmdclass={'install_data': Canto_install_data}
)
