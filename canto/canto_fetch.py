#Canto - ncurses RSS reader
#   Copyright (C) 2008 Jack Miller <jack@codezen.org>
#
#   This program is free software; you can redistribute it and/or modify
#   it under the terms of the GNU General Public License version 2 as 
#   published by the Free Software Foundation.

import cPickle
import codecs
import getopt
import time
import os
import feedparser
import shutil
import sys

def main(cfg, optlist, verbose=False, force=False):

    for opt, arg in optlist:
        if opt in ["-V","--verbose"]:
            verbose = True
        elif opt in ["-f","--force"]:
            force = True

    # Because canto-fetch isn't an ncurses application,
    # we might actually want to print to the screen!

    def log_func(x):
        if verbose:
            print x
        cfg.log(x)

    # Make sure that the feed_dir does, indeed, exist and is
    # actually a directory.

    if not os.path.exists(cfg.feed_dir):
        os.mkdir(cfg.feed_dir)
    elif not os.path.isdir(cfg.feed_dir):
        os.unlink(cfg.feed_dir)
        os.mkdir(cfg.feed_dir)

    # Rename any < 0.5.5 tag named files with > 0.5.5 URL named files.

    for file in os.listdir(cfg.feed_dir):
        for tag, URL in [(f.tag, f.URL) for f in cfg.feeds \
                if hasattr(f,"tag") ]:
            if file == tag.replace("/"," "):
                log_func("Detected old disk format, converting.")
                target = cfg.feed_dir + file
                newname = cfg.feed_dir + URL.replace("/"," ")
                os.rename(target, newname)
                break

    # Remove any crap out of the directory. This is mostly for
    # cleaning up when the user has removed a feed from the configuration.

    for file in os.listdir(cfg.feed_dir):
        for URL in [f.URL for f in cfg.feeds]:
            valid = URL.replace("/"," ")
            if file == valid or file == valid + ".lock":
                break
        else:
            log_func("Deleted extraneous file: %s" % file)
            try:
                os.unlink(cfg.feed_dir + file)
            except:
                pass

    # The main canto-fetch loop.

    for fd in cfg.feeds:
        fpath = cfg.feed_dir + fd.URL.replace("/", " ")
        lpath = fpath + ".lock"

        # First, we get a lock.

        try:
            lock = os.open(lpath, os.O_CREAT|os.O_EXCL)
        except OSError:
            # If lock exists, but is over 2 minutes old, it's
            # probably the product of a crash or a machine
            # getting powered down, delete it.

            if time.time() - os.stat(lpath).st_ctime > 120:
                log_func("Deleting stale lock for %s." % fd.URL)
                os.unlink(lpath)
                try:
                    lock = os.open(lpath, os.O_CREAT|os.O_EXCL)
                except:
                    # Failing twice should be exceptionally rare (because
                    # that would indicate that between the unlink and
                    # the os.open another process created it.

                    log_func("Failed twice to get lock for %s." % fd.URL)
                    continue
            else:
                # Failing once is pretty typical, and not fatal.
                log_func("Failed once to get lock for %s." % fd.URL)
                continue

        # locks must be closed to avoid having a million
        # dangling file descriptors and eventually killing the program.

        os.close(lock)

        update(fd, fpath, force, log_func)

        # Finally, release the lock. This is wrapped in a 
        # try->catch because sometimes the lock disappears
        # (either through user intervention or an error)
        # and it should not be fatal.

        try:
            os.unlink(lpath)
        except:
            log_func("Failed to release lock for %s" % fd.tag)
    
    log_func("Gracefully exiting Canto-fetch.")
    return 0

def update(fd, fpath, force, log_func):
    # This emptyfeed forms a skeleton for any canto feed.
    # Canto_state is a place holder. Canto_update is the
    # last time the feed was updated, and canto_version is
    # obviously the version under which it was last written.

    # Canto_version will be used in the future, if later
    # releases change anything serious in the format.

    emptyfeed = {"canto_state":[], "entries":[], "canto_update":0, 
                    "canto_version":VERSION_TUPLE}

    # Now we attempt to load the previous feed information.

    if os.path.exists(fpath):
        if os.path.isfile(fpath):
            f = open(fpath, "rb")
            try:
                curfeed = cPickle.load(f)
            except:
                log_func("cPickle load exception on %s" % fpath)
                return
            f.close()
        else:
            # This is a directory, then it's most likely a 
            # canto < 0.5.0 info, so we kill it.

            log_func("%s is not normal file, old format?" % fpath)
            log_func("  Deleting...")
            if os.path.isdir(fpath):
                shutil.rmtree(fpath)
            else:
                os.unlink(fpath)
            curfeed = emptyfeed
    else:
        curfeed = emptyfeed

    # Determine whether it's been long enough between
    # updates to warrant refetching the feed.

    if time.time() - curfeed["canto_update"] < fd.rate * 60 and not force:
        return

    # Attempt to set the tag, if unspecified, by grabbing
    # it out of the previously downloaded info.

    if not hasattr(fd,"tag"):
        if curfeed.has_key("feed") and curfeed["feed"].has_key("title"):
            fd.tag = curfeed["feed"]["title"]
            log_func("Updating %s" % fd.tag)
        else:
            # This is the first time we've gotten this URL,
            # so just use the URL since we don't know the title.

            log_func("New feed %s" % fd.URL)
    else:
        log_func("Updating %s" % fd.tag)

    try:
        newfeed = feedparser.parse(feedparser.urllib2.urlopen(fd.URL))
    except:
        # Generally an exception is a connection refusal, but in any
        # case we either won't get data or can't trust the data, so
        # just skip processing this feed.

        log_func("Exception trying to get feed: %s" % sys.exc_info()[1])
        return

    if not hasattr(fd,"tag"):
        if newfeed.has_key("feed") and newfeed["feed"].has_key("title"):
            fd.tag = newfeed["feed"]["title"].encode("UTF-8")
        else:
            log_func("Ugh. Defaulting to URL for tag. No guarantees.")
            newfeed["feed"]["title"] = fd.URL
            fd.tag = fd.URL

    # Feedparser returns a very nice dict of information.
    # if there was something wrong with the feed (usu. encodings
    # being mis-declared or missing tags), it sets
    # bozo_exception.

    # These exceptions are recoverable and their objects are
    # un-Picklable so we log it and remove the value.

    if newfeed.has_key("bozo_exception"):
        log_func("Recoverable error in feed %s: %s" % 
                    (fd.tag, newfeed["bozo_exception"]))
        newfeed["bozo_exception"] = None

    # Make state persist between feeds
    newfeed["canto_state"] = curfeed["canto_state"]
    newfeed["canto_update"] = time.time()
    
    # For all content that we would usually use, we convert
    # it to UTF-8 and escape all %s with \. Feedparser
    # almost without exception gives us all string in Unicode
    # so none of these should fail.

    def encode_and_escape(s):
        s = s.encode("UTF-8")
        s = s.replace("\\","\\\\")
        return s.replace("%", "\\%")

    for key in newfeed["feed"]:
        if type(newfeed["feed"][key]) in [unicode,str]:
            newfeed["feed"][key] = encode_and_escape(newfeed["feed"][key])

    for entry in newfeed["entries"]:
        if entry.has_key("content"):
            for c in entry["content"]:
                c["value"] = encode_and_escape(c["value"])

        for key in entry.keys():
            if type(entry[key]) in [unicode,str]:
                entry[key] = encode_and_escape(entry[key])

    for entry in newfeed["entries"]:
        # If the item didn't come with a GUID, then
        # use link and then title as an identifier.

        if not entry.has_key("id"):
            if entry.has_key("link"):
                entry["id"] = entry["link"]
            elif entry.has_key("title"):
                entry["id"] = entry["title"]
            else:
                entry["id"] = None

        # Then search through the current feed to
        # make item state persistent.

        for centry in curfeed["entries"]:
            if entry["id"] == centry["id"]:
                entry["canto_state"] = centry["canto_state"]
                
                # The entry is removed so that later it's
                # not a candidate for being appended to the
                # end of the feed.

                curfeed["entries"].remove(centry)
                break

        # Apply default state to genuinely new items.
        if not entry.has_key("canto_state"):
            entry["canto_state"] = [ fd.tag, "unread", "*", "new"]

    # Tailor the list to the correct number of items.
    if len(newfeed["entries"]) < fd.keep:
        newfeed["entries"] += \
            curfeed["entries"][:fd.keep - len(newfeed["entries"])]
    else:
        newfeed["entries"] = newfeed["entries"][:fd.keep]

    # Dump the output to the new file.
    f = open(fpath, "wb")
    try:
        cPickle.dump(newfeed, f)
    except:
        log_func("cPickle dump exception on %s" % fpath)
        raise
    f.close()
