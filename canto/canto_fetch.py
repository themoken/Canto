#Canto - ncurses RSS reader
#   Copyright (C) 2008 Jack Miller <jack@codezen.org>
#
#   This program is free software; you can redistribute it and/or modify
#   it under the terms of the GNU General Public License version 2 as 
#   published by the Free Software Foundation.

# Canto-fetch is essentially a stand alone binary, it's only packaged with the
# canto client source because they share configuration and canto-fetch can
# conveniently fit into a single file without there being too much confusion.

# There are three parts, roughly.
# main()        -> arg parsing and (if necessary) runs the daemon loop
# run()         -> spawns the appropriate threads
# FetchThread   -> performs the update for one feed

# main is only used when canto-fetch is called from the command line.
# run is used internally by canto when it needs to invoke an update.

from const import VERSION_TUPLE
from cfg.base import get_cfg
import utility
import args

from threading import Thread
import feedparser
import traceback
import commands
import urlparse
import urllib2
import cPickle
import socket
import signal
import fcntl
import time
import sys
import os

def main(enc):
    conf_dir, log_file, conf_file, feed_dir, script_dir, optlist =\
        args.parse_common_args(enc,
            "hvVfdbi:", ["help","version","verbose","force","daemon",\
                    "background", "interval="], "canto-fetch")

    try :
        cfg = get_cfg(conf_file, log_file, feed_dir, script_dir)
        cfg.parse()
    except :
        traceback.print_exc()
        sys.exit(-1)

    def log_func(x):
        if verbose:
            print x
        cfg.log(x)

    #Defaults
    updateInterval = 60
    daemon = False
    background = False
    verbose = False
    force = False

    for opt, arg in optlist :
        if opt in ["-d","--daemon"]:
            daemon = True
        if opt in ["-b","--background"]:
            background = True
            daemon = True
        if opt in ["-i","--interval"]:
            try:
                arg = unicode(arg, enc, "ignore")
                i = int(arg)
                if i < 60:
                    cfg.log("interval must be >= 60 (one minute)")
                else:
                    updateInterval = i
            except:
                cfg.log("%s isn't a valid interval" % arg)
            else:
                cfg.log("interval = %d seconds" % updateInterval)
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

    if background:
        # This is a pretty canonical way to do backgrounding.

        pid = os.fork()
        if not pid:
            # New terminal session
            os.setsid()

            os.chdir("/")
            os.umask(0)
            pid = os.fork()
            if pid:
                sys.exit(0)
        else:
            sys.exit(0)

        # Close all possible terminal output
        # file descriptors. 

        os.close(0)
        os.close(1)
        os.close(2)

    if daemon:
        while 1:
            run(cfg, verbose, force)
            time.sleep(updateInterval)
            oldcfg = cfg
            try :
                cfg = get_cfg(conf_file, log_file, feed_dir, script_dir)
                self.cfg.parse()
            except:
                cfg = oldcfg
    else:
        sys.exit(run(cfg, verbose, force))

def run(cfg, verbose=False, force=False):

    # If we don't explicitly set this, feedparser/urllib will take *forever* to
    # give up on a connection. 30 is a pretty sane default, I think, considering
    # that 30 seconds is more than enough time to get your average 4-5k feed
    # even on a really poor connection.

    socket.setdefaulttimeout(30)

    threads = []

    def log_func(x):
        if verbose:
            print x
        cfg.log(x)

    def imdone():
        if threads != []:
            for thread in threads:
                thread.join()
        socket.setdefaulttimeout(None)
        log_func("Gracefully exiting Canto-fetch.")
        return 1

    killme = lambda a, b: imdone() and sys.exit(0)

    signal.signal(signal.SIGTERM, killme)
    signal.signal(signal.SIGINT, killme)

    # The main canto-fetch loop.
    for fd in cfg.feeds:
        fpath = cfg.feed_dir + fd.URL.replace("/", " ")
        spath = cfg.script_dir
        threads.append(FetchThread(cfg, fd, fpath, spath, force, log_func))
        threads[-1].daemon = True
        threads[-1].start()

    imdone()
    return 0

class FetchThread(Thread):
    def __init__(self, cfg, fd, fpath, spath, force, log_func):
        Thread.__init__(self)
        self.fd = fd
        self.fpath = fpath
        self.spath = spath
        self.force = force
        self.cfg = cfg
        self.log_func = log_func
        self.prevtime = 0

        # This emptyfeed forms a skeleton for any canto feed.
        # Canto_state is a place holder. Canto_update is the
        # last time the feed was updated, and canto_version is
        # obviously the version under which it was last written.

        # Canto_version will be used in the future, if later
        # releases change anything serious in the format.

        self.emptyfeed = {"canto_state":[], "entries":[], "canto_update":0,
                        "canto_version": VERSION_TUPLE }

    # get_curfeed loads the old feed data from disk. It blocks getting the lock,
    # so it could take awhile, but should never fail if the information isn't
    # corrupted.

    def get_curfeed(self):
        curfeed = self.emptyfeed
        if os.path.exists(self.fpath):
            if os.path.isfile(self.fpath):
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
        else:

            # The file doesn't exist yet, so we write a stub so that Canto
            # detects presence and doesn't endlessly try to refetch error'd
            # feeds if later on an error occurs.

            d = { u"title" : u"No content.",
                    u"description" : u"There's no content in this feed. It's" +
                    " possible that it hasn't been fetched yet or an error was" +
                    " encountered. Check your fetchlog.",
                    u"canto_state" : ["*"],
                    u"id" : u"canto-internal"
                }

            curfeed["entries"].append(d)
            f = open(self.fpath, "w")
            try:
                fcntl.flock(f.fileno(), fcntl.LOCK_EX)
                cPickle.dump(curfeed, f)
                f.flush()
            except:
                pass
            finally:
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)
                f.close()

        return curfeed

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

        # This block set newfeed to a parsed feed.

        try:
            # Feed from script
            if self.fd.URL.startswith("script:"):
                script = self.spath + "/" + self.fd.URL[7:]
                out = commands.getoutput(script)
                newfeed = feedparser.parse(out)
            # Feed from URL
            else:
                request = urllib2.Request(self.fd.URL)
                request.add_header('User-Agent',\
                    "Canto/%d.%d.%d + http://codezen.org/canto" %\
                    VERSION_TUPLE)

                # Feed from URL w/ password
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
                # Feed with no password.
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

        # Filter out "No Content" message since we apparently have real content

        curfeed["entries"] = [ x for x in curfeed["entries"] if x["id"] !=\
                "canto-internal"]

        # For new feeds whose base tag is still not set, attempt to get a title
        # again.

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

        # Make state persist between feeds. Currently, this is completely
        # unused, as there's no state information that needs to be propagated.
        # This is a relic from when feeds and tags were the same thing, however
        # it could be useful when doing integration with another client /
        # website and thus, hasn't been removed.

        newfeed["canto_state"] = curfeed["canto_state"]
        newfeed["canto_update"] = time.time()

        # We can set this here, without checking curfeed.
        # Any migration should be done in the get_curfeed function,
        # when the old data is first loaded.

        newfeed["canto_version"] = VERSION_TUPLE

        # For all content that we would usually use, we escape all of the
        # slashes and other potential escapes.

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

        new = []
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
                else:
                    new.append(entry)

                # Apply default state to genuinely new items.
                if "canto_state" not in entry:
                    entry["canto_state"] = self.fd.tags + [u"*"]

            # Tailor the list to the correct number of items. In canto < 0.7.0,
            # you could specify a keep that was lower than the number of items
            # in the feed. This was simply done, but ultimately it caused too
            # much "bounce" for social news feeds. Items get put into the feed,
            # are upvoted enough to be within the first n items, you change
            # their state, they move out of the first n items, are forgotten,
            # then are upvoted again into the first n item and (as far as c-f
            # knows) are treated like brand new items.

            # This will still be a problem if items get taken out of the feed
            # and put back into the feed (and the item isn't in the extra kept
            # items), but then it becomes a site problem, not a reader problem.

            if self.fd.keep and len(newfeed["entries"]) < self.fd.keep:
                newfeed["entries"] += curfeed["entries"]\
                        [:self.fd.keep - len(newfeed["entries"])]

            # Enforce the "never_discard" setting
            # We iterate through the stories and then the tag so that
            # feed order is preserved.

            for e in curfeed["entries"]:
                for tag in self.cfg.never_discard:
                    if tag == "unread":
                        if "read" in e["canto_state"]:
                            continue
                    elif tag not in e["canto_state"]:
                        continue
                    if e not in newfeed["entries"]:
                        newfeed["entries"].append(e)

            if self.cfg.new_hook:
                for entry in [e for e in new if e in newfeed["entries"]]:
                    self.cfg.new_hook(newfeed, entry, entry == new[-1])

            # Dump the output to the new file.

            # Locking and writing is counter-intuitive using fcntl. If you open
            # with "w" and fail to get the lock, the data is still deleted. The
            # solution is to open with "a", get the lock and then truncate the
            # file.

            f = open(self.fpath, "a")
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)

            # The feed was modified out from under us.
            if self.prevtime and self.prevtime != os.stat(self.fpath).st_mtime:
                # Unlock.
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)
                f.close()

                # Reread the state from disk.
                newer_curfeed = self.get_curfeed()

                # There was an actual c-f update done, bail.
                if newer_curfeed["canto_update"] != curfeed["canto_update"]:
                    self.log_func("%s updated already, bailing" %
                            self.fd.tags[0])
                    break

                # Just a state modification by the client, update and continue.
                else:
                    curfeed = newer_curfeed
                    continue

            # Truncate the file
            f.seek(0, 0)
            f.truncate()

            try:
                # Dump the feed item. It's important to flush afterwards to
                # avoid unlocking the file before all the IO is finished.
                cPickle.dump(newfeed, f)
                f.flush()
            except:
                self.log_func("cPickle dump exception on %s" % self.fpath)
            finally:
                # Unlock.
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)
                f.close()

            # If we managed to write to disk, break out of the while loop and
            # the thread will exit.

            break

