#!/usr/bin/env python
from __future__ import with_statement # This isn't required in Python 2.6
import commands
import distutils.core
import distutils.command.install_data
import uninstall
version = ['0','7','9']
man_date = "24 May 2010"
git_commit = commands.getoutput("git show --pretty=oneline\
        --abbrev-commit").split()[0]

# TODO: replace with build_manpages target (@james will do this shortly if approved)
class Canto_install_data(distutils.command.install_data.install_data):
    def run(self):
        ret = distutils.command.install_data.install_data.run(self)

        install_cmd = self.get_finalized_command('install')
        libdir = install_cmd.install_lib
        mandir = install_cmd.install_data + "/share/man/man1/"

        for source in ["/canto/const.py"]:
            with open(libdir + source, "r+") as f:
                d = f.read().replace("SET_VERSION_TUPLE","(" +\
					",".join(version) + ")")
                d = d.replace("SET_GIT_SHA", "\"" + git_commit + "\"")
                f.truncate(0)
                f.seek(0)
                f.write(d)

        for manpage in ["canto.1","canto-fetch.1","canto-inspect.1"]:
            with open(mandir + manpage, "r+") as f:
                d = f.read().replace("MAN_VERSION", ".".join(version))
                d = d.replace("MAN_DATE", man_date)
                f.truncate(0)
                f.seek(0)
                f.write(d)

distutils.core.setup(name='Canto',
        version=".".join(version),
        description='An ncurses RSS aggregator.',
        author='Jack Miller',
        author_email='jack@codezen.org',
        url='http://codezen.org/canto',
        download_url='http://codezen.org/static/canto-' + ".".join(version) + ".tar.gz",
        platforms=["linux"],
        license='GPLv2',
        scripts=['bin/canto','bin/canto-fetch', 'bin/canto-inspect'],
        packages=['canto', 'canto.cfg'],
        ext_modules=[distutils.core.Extension('canto.widecurse',\
                sources = ['canto/widecurse.c'], libraries = ['ncursesw'],
                library_dirs=["/usr/local/lib", "/opt/local/lib"],
                include_dirs=["/usr/local/include", "/opt/local/include"])],
        data_files = [("share/man/man1/",\
                ["man/canto.1", "man/canto-fetch.1", "man/canto-inspect.1"])],
        cmdclass={
		'install_data': Canto_install_data,
		'install': uninstall.install, 'uninstall': uninstall.uninstall
	}
)
