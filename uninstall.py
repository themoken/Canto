#!/usr/bin/python
# -*- coding: utf-8 -*-
"""distutils.command.uninstall

Uninstall/install targets for python distutils.
Implements the Distutils 'uninstall' command and a replacement (inheriting)
install command to add in the hooks to make the uninstall command happy.
"""

# Copyright (C) 2009  James Shubin, McGill University
# Written for McGill University by James Shubin <purpleidea@gmail.com>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

# created 2009/10/10, James Shubin

from __future__ import with_statement

__revision__ = "$Id$"		# TODO: what should i do with this?

import os
import distutils.core
import distutils.command.install
import distutils.errors


# TODO: have the get stored away as part of the install somewhere
INSTALL_LOG = 'install.log'	# default filename for install log

_ = lambda x: x			# add fake gettext function until i fix up i18n
__all__ = ['install', 'uninstall']

# NOTE: PEP376 might eventually support (automatic?) uninstall, until then...
# see: http://www.python.org/dev/peps/pep-0376/ or search the internets.
class install(distutils.command.install.install):
	"""inherit from the main install, replacing it."""
	# NOTE: don't add any functions in this class without calling the parent!
	def run(self):
		if self.verbose: print _('running custom install')
		# run whatever was supposed to run from the main install
		# NOTE: this respects the dry-run option.
		distutils.command.install.install.run(self)

		# ...and then add on some hooks to support uninstalling.
		if not(self.dry_run):
			try:
				with open(INSTALL_LOG, 'w') as f:
					# note: use '\n' for *all* platforms, not just linux.
					# see: http://docs.python.org/library/os.html#os.linesep
					f.write(_('# installed files log. needed for uninstall. do NOT delete.\n'))
					f.writelines([ '%s\n' % x for x in self.get_outputs() ])
			except IOError, e:
				print _('unable to write install log to: %s') % INSTALL_LOG
				print e


class uninstall(distutils.core.Command):
	description = _('uninstalls a python package, trying its best to succeed')
	user_options = [
		('force-log', 'L', _('uninstall from install log data')),
		('force-guess', 'G', _('uninstall based on a dry-run install')),
		('install-log=', 'f', _('specifies the install log file to use')),
		('generate-log=', 'g', _('generates a dry-run log file')),
		# TODO: someone annoying can add this if they're scared :)
		#('always-ask=', 'a', _('prompt before every removal')),
		# TODO: add this option.
		#('purge-config', 'P', _('purge all traces of config'))
	]


	def initialize_options(self):
		self.force_log = None
		self.force_guess = None
		self.install_log = None
		self.generate_log = None
		self.always_ask = None
		self.purge_config = None


	def finalize_options(self):
		# uninstaller has to try one method or the other, not both.
		# if neither is set, then uninstaller gets to choose.
		if self.force_log and self.force_guess:
			raise distutils.errors.DistutilsOptionError(
			_('choose either the `force-log\' or `force-guess\' option.')
			)

		# do some validation
		if (self.install_log is not None) and not(os.path.exists(self.install_log)):
			raise distutils.errors.DistutilsOptionError(
			_('the `install-log\' option must point to an existing file.')
			)


	def run(self):
		success = False
		# do this unless we are forced to guess
		if not(self.force_guess):
			filename = INSTALL_LOG	# the default
			if self.install_log is not None:	# override if specified
				filename = self.install_log
			try:
				with open(filename, 'r') as f:
					# take out the comments
					filelist = [ x.strip() for x in f.readlines() if x[0] != '#' ]
				success = True	# this worked
			except IOError, e:
				if self.force_log:
					print _('unable to read install log at: %s') % filename
					print e
					return	# must exit this function

		# we assume that as a backup, we can `depend' on this heuristic
		if self.generate_log or (not(success) and not(self.force_log)):
			if self.verbose: print _('running guess')
			output = self.get_install_outputs()
			# success logically represents if we are depending on `guess'
			if not success: filelist = output
			# also generate the log if asked
			if self.generate_log and not(self.dry_run):
				try:
					with open(self.generate_log) as f:
						f.write(_('# installed files guess log.\n'))
						f.writelines([ '%s\n' % x for x in output ])
				except IOError, e:
					print _('unable to write install guess log to: %s') % self.generate_log
					print e

		# document the type of uninstall that the data is coming from
		if self.verbose:
			if success: print _('uninstalling from log: %s' % filename)
			else: print _('uninstalling from guess')

		# given the list of files, process them and delete here:
		dirlist = []
		for x in filelist:
			if not(os.path.exists(x)):
				print _('missing: %s') % x
			elif os.path.isfile(x):
				# collect dirs which install log doesn't store
				dirlist.append(os.path.split(x)[0])
				self.__os_rm(x)
				# remove any .pyc, pyo & (pyw: should we?) mess
				if os.path.splitext(x)[1] == '.py':
					for ext in ('c', 'o'):	# add 'w' ?
						mod = x + ext
						if self.__os_rm(mod):
							# don't remove it twice
							if mod in filelist:
								filelist.remove(mod)
			# save for later
			elif os.path.isdir(x):
				dirlist.append(x)

		if len(dirlist) == 0: return
		dirlist = list(set(dirlist))	# remove duplicates
		# loop through list until it stops changing size.
		# this way we know all directories have been pruned.
		# most robust if someone shoves in a weird install log.
		if self.verbose: print _('attempting to remove directories...')
		while True:
			size = len(dirlist)
			if size == 0:
				if self.verbose: print _('successfully removed all directories.')
				break
			for x in dirlist:
				# keep non-empty dirs
				if len(os.listdir(x)) == 0:
					if self.__os_rm(x):
						dirlist.remove(x)

			if len(dirlist) == size:
				print _('couldn\'t remove any more directories')
				print _('directories not removed include:')
				for i in dirlist:
					print '\t* %s' % i
				break


	def get_install_outputs(self):
		"""returns the get_outputs() list of a dry run installation."""
		self.distribution.dry_run = 1	# do this under a dry run
		self.run_command('install')
		return self.get_finalized_command('install').get_outputs()


	def __os_rm(self, f):
		"""simple helper function to aid with code reuse."""
		if os.path.exists(f):
			if self.verbose: print _('removing: %s') % f
			if not(self.dry_run):
				try:
					if os.path.isdir(f): os.rmdir(f)
					else: os.remove(f)
					return True
				except OSError, e:
					if self.verbose: print _('couldn\'t remove: %s') % f
					return False

