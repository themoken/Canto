#!/usr/bin/env python
from __future__ import with_statement # This isn't required in Python 2.6
from distutils.core import setup, Extension
from distutils.command.install_data import install_data

version = ['0','6','13']
man_date = "12 May 2009"

class Canto_install_data(install_data):
    def run(self):
        ret = install_data.run(self)

        install_cmd = self.get_finalized_command('install')
        libdir = install_cmd.install_lib
        mandir = install_cmd.install_data + "/share/man/man1/"

        for source in ["/canto/const.py"]:
            with open(libdir + source, "r+") as f:
                d = f.read().replace("SET_VERSION_TUPLE","(" +\
                        ",".join(version) + ")")
                f.truncate(0)
                f.seek(0)
                f.write(d)

        for manpage in ["canto.1","canto-fetch.1"]:
            with open(mandir + manpage, "r+") as f:
                d = f.read().replace("MAN_VERSION", ".".join(version))
                d = d.replace("MAN_DATE", man_date)
                f.truncate(0)
                f.seek(0)
                f.write(d)

setup(name='Canto',
        version=".".join(version),
        description='An ncurses RSS aggregator.',
        author='Jack Miller',
        author_email='jack@codezen.org',
        url='http://codezen.org/canto',
        license='GPLv2',
        scripts=['bin/canto','bin/canto-fetch'],
        packages=['canto'],
        ext_modules=[Extension('canto.widecurse',\
                sources = ['canto/widecurse.c'], libraries = ['ncursesw'],
                library_dirs=["/usr/local/lib", "/opt/local/lib"],
                include_dirs=["/usr/local/include", "/opt/local/include"])],
        data_files = [("share/man/man1/", ["man/canto.1", "man/canto-fetch.1"])],
        cmdclass={'install_data': Canto_install_data}
)
