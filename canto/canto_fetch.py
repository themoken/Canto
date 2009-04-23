#Canto - ncurses RSS reader
#   Copyright (C) 2008 Jack Miller <jack@codezen.org>
#
#   This program is free software; you can redistribute it and/or modify
#   it under the terms of the GNU General Public License version 2 as 
#   published by the Free Software Foundation.

from const import VERSION_TUPLE

from threading import Thread
import feedparser
import commands
import urlparse
import urllib2
import cPickle
import socket
import signal
import shutil
import fcntl
import time
import sys
import os

def main(cfg, optlist, verbose=False, force=False):

    socket.setdefaulttimeout(30)

    threads = []

    # Because canto-fetch isn't an ncurses application,
    # we might actually want to print to the screen!

    def log_func(x):
        if verbose:
            print x
        cfg.log(x)

    def imdone():
        if threads != []:
            for thread in threads:
                thread.join()
        log_func("Gracefully exiting Canto-fetch.")
        return 1

    killme = lambda a, b: imdone() and sys.exit(0)

    signal.signal(signal.SIGTERM, killme)
    signal.signal(signal.SIGINT, killme)

    for opt,arg in optlist:
        if opt in ["-V","--verbose"]:
            verbose = True
        elif opt in ["-f","--force"]:
            force = True

    # Make sure that the feed_dir does, indeed, exist and is
    # actually a directory.

    if not os.path.exists(cfg.feed_dir):
        os.mkdir(cfg.feed_dir)
    elif not os.path.isdir(cfg.feed_dir):
        os.unlink(cfg.feed_dir)
        os.mkdir(cfg.feed_dir)

    # Remove any crap out of the directory. This is mostly for
    # cleaning up when the user has removed a feed from the configuration.

    valid_names = [f.URL.replace("/"," ") for f in cfg.feeds]
    for file in os.listdir(cfg.feed_dir):
        if not file in valid_names:
            log_func("Deleted extraneous file: %s" % file)
            try:
                os.unlink(cfg.feed_dir + file)
            except:
                pass

    # The main canto-fetch loop.
    for fd in cfg.feeds:
        fpath = cfg.feed_dir + fd.URL.replace("/", " ")
        spath = cfg.script_dir
        threads.append(UpdateThread(fd, fpath, spath, force, log_func))
        threads[-1].start()

    imdone()
    return 0

class UpdateThread(Thread):
    def __init__(self, fd, fpath, spath, force, log_func):
        Thread.__init__(self)
        self.fd = fd
        self.fpath = fpath
        self.spath = spath
        self.force = force
        self.log_func = log_func
        self.prevtime = 0

        # This emptyfeed forms a skeleton for any canto feed.
        # Canto_state is a place holder. Canto_update is the
        # last time the feed was updated, and canto_version is
        # obviously the version under which it was last written.

        # Canto_version will be used in the future, if later
        # releases change anything serious in the format.

        self.emptyfeed = {"canto_state":[], "entries":[], "canto_update":0,
                        "canto_version":VERSION_TUPLE}

    def get_curfeed(self):
        curfeed = self.emptyfeed
        if os.path.exists(self.fpath) and os.path.isfile(self.fpath):
            f = open(self.fpath, "r")
            fcntl.flock(f.fileno(), fcntl.LOCK_SH)

            self.prevtime = os.stat(self.fpath).st_mtime

            try:
                curfeed = cPickle.load(f)
            except:
                self.log_func("cPickle load exception on %s" % self.fpath)
            finally:
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)
                f.close()

        return curfeed

    # Now we attempt to load the previous feed information.

    def run(self):
        curfeed = self.get_curfeed()

        # Determine whether it's been long enough between
        # updates to warrant refetching the feed.

        if time.time() - curfeed["canto_update"] < self.fd.rate * 60 and\
                not self.force:
            return

        # Attempt to set the tag, if unspecified, by grabbing
        # it out of the previously downloaded info.

        if not self.fd.base_set:
            if "feed" in curfeed and "title" in curfeed["feed"]:
                replace = lambda x: x or curfeed["feed"]["title"]
                self.fd.tags = [ replace(x) for x in self.fd.tags]
                self.fd.base_set = 1
                self.log_func("Updating %s" % self.fd.tags[0])
            else:
                # This is the first time we've gotten this URL,
                # so just use the URL since we don't know the title.

                self.log_func("New feed %s" % self.fd.URL)
        else:
            self.log_func("Updating %s" % self.fd.tags[0])

        try:
            if self.fd.URL.startswith("script:"):
                script = self.spath + "/" + self.fd.URL[7:]
                out = commands.getoutput(script)
                newfeed = feedparser.parse(out)
            else:
                request = urllib2.Request(self.fd.URL)
                request.add_header('User-Agent',\
                    "Canto/%d.%d.%d + http://codezen.org/canto" %\
                    VERSION_TUPLE)

                if self.fd.username or self.fd.password:
                    mgr = urllib2.HTTPPasswordMgrWithDefaultRealm()
                    domain = urlparse.urlparse(self.fd.URL)[1]
                    mgr.add_password(None, domain,\
                            self.fd.username, self.fd.password)

                    # First, we try Basic Authentication
                    auth = urllib2.HTTPBasicAuthHandler(mgr)
                    opener = urllib2.build_opener(auth)
                    try:
                        newfeed = feedparser.parse(opener.open(request))
                    except:
                        # And, failing that, try Digest Authentication
                        auth = urllib2.HTTPDigestAuthHandler(mgr)
                        opener = urllib2.build_opener(auth)
                        newfeed = feedparser.parse(opener.open(request))
                else:
                    newfeed = feedparser.parse(\
                            feedparser.urllib2.urlopen(request))
        except:
            # Generally an exception is a connection refusal, but in any
            # case we either won't get data or can't trust the data, so
            # just skip processing this feed.

            self.log_func("Exception trying to get feed %s : %s" % \
                    (self.fd.tags[0], sys.exc_info()[1]))
            return

        # I don't know why feedparser doesn't actually throw this
        # since all URLErrors are basically unrecoverable.

        if "bozo_exception" in newfeed:
            if type(newfeed["bozo_exception"]) == urllib2.URLError:
                self.log_func(\
                    "Feedparser exception getting %s : %s, bailing." %\
                    (self.fd.URL, newfeed["bozo_exception"].reason))
                return
            if not len(newfeed["entries"]):
                self.log_func(\
                    "Feedparser exception, no content in %s : %s, bailing." %\
                    (self.fd.URL, newfeed["bozo_exception"]))
                return

        if not self.fd.base_set:
            if "feed" not in newfeed or "title" not in newfeed["feed"]:
                self.log_func("Ugh. Defaulting to URL for tag. No guarantees.")
                newfeed["feed"]["title"] = self.fd.URL

            replace = lambda x: x or newfeed["feed"]["title"]
            self.fd.tags = [ replace(x) for x in self.fd.tags]

        # Feedparser returns a very nice dict of information.
        # if there was something wrong with the feed (usu. encodings
        # being mis-declared or missing tags), it sets
        # bozo_exception.

        # These exceptions are recoverable and their objects are
        # un-Picklable so we log it and remove the value.

        if "bozo_exception" in newfeed:
            self.log_func("Recoverable error in feed %s: %s" % 
                        (self.fd.tags[0], newfeed["bozo_exception"]))
            newfeed["bozo_exception"] = None

        # Make state persist between feeds
        newfeed["canto_state"] = curfeed["canto_state"]
        newfeed["canto_update"] = time.time()

        # We can set this here, without checking curfeed.
        # Any migration should be done in the get_curfeed function,
        # when the old data is first loaded.

        newfeed["canto_version"] = VERSION_TUPLE

        # For all content that we would usually use, we convert
        # it to UTF-8 and escape all %s with \. Feedparser
        # almost without exception gives us all string in Unicode
        # so none of these should fail.

        def escape(s):
            s = s.replace("\\","\\\\")
            return s.replace("%", "\\%")

        for key in newfeed["feed"]:
            if type(newfeed["feed"][key]) in [unicode,str]:
                newfeed["feed"][key] = escape(newfeed["feed"][key])

        for entry in newfeed["entries"]:
            for subitem in ["content","enclosures"]:
                if subitem in entry:
                    for e in entry[subitem]:
                        for k in e.keys():
                            if type(e[k]) in [unicode,str]:
                                e[k] = escape(e[k])

            for key in entry.keys():
                if type(entry[key]) in [unicode,str]:
                    entry[key] = escape(entry[key])

        for entry in newfeed["entries"]:
            # If the item didn't come with a GUID, then
            # use link and then title as an identifier.

            if not "id" in entry:
                if "link" in entry:
                    entry["id"] = entry["link"]
                elif "title" in entry:
                    entry["id"] = entry["title"]
                else:
                    entry["id"] = None

        # Then search through the current feed to
        # make item state persistent, and loop until
        # it's safe to update on disk.

        while 1:
            for entry in newfeed["entries"]:
                for centry in curfeed["entries"]:
                    if entry["id"] == centry["id"]:
                        entry["canto_state"] = centry["canto_state"]
                        
                        # The entry is removed so that later it's
                        # not a candidate for being appended to the
                        # end of the feed.

                        curfeed["entries"].remove(centry)
                        break

                # Apply default state to genuinely new items.
                if not "canto_state" in entry:
                    entry["canto_state"] = self.fd.tags + \
                            [u"*", u"new"]

            # Tailor the list to the correct number of items.
            if len(newfeed["entries"]) < self.fd.keep:
                newfeed["entries"] += \
                    curfeed["entries"][:self.fd.keep - len(newfeed["entries"])]
            else:
                newfeed["entries"] = newfeed["entries"][:self.fd.keep]

            # Dump the output to the new file.
            f = open(self.fpath, "a")
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)

            # The feed was modified out from under us.
            if self.prevtime and self.prevtime != os.stat(self.fpath).st_mtime:
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)
                f.close()

                newer_curfeed = self.get_curfeed()

                # There was an actual c-f update done, bail
                if newer_curfeed["canto_update"] != curfeed["canto_update"]:
                    self.log_func("%s updated already, bailing" %
                            self.fd.tags[0])
                    break

                # Just a state modification by the client, update and continue.
                else:
                    curfeed = newer_curfeed
                    continue

            f.seek(0, 0)
            f.truncate()
            try:
                cPickle.dump(newfeed, f)
                f.flush()
            except:
                self.log_func("cPickle dump exception on %s" % self.fpath)
            finally:
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)
                f.close()

            break

