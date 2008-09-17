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


def main(cfg, optlist, verbose=False, force=False):

    for opt, arg in optlist:
        if opt in ["-V","--verbose"]:
            verbose = True
        elif opt in ["-f","--force"]:
            force = True

    def log_func(x):
        if verbose:
            print x
        cfg.log(x)

    emptyfeed = {"canto_state":[], "entries":[], "canto_update":0, 
                    "canto_version":VERSION_TUPLE}

    if not os.path.exists(cfg.feed_dir):
        os.mkdir(cfg.feed_dir)
    elif not os.path.isdir(cfg.feed_dir):
        os.unlink(cfg.feed_dir)
        os.mkdir(cfg.feed_dir)

    for file in os.listdir(cfg.feed_dir):
        file = cfg.feed_dir + file
        for tag in [f.tag for f in cfg.feeds]:
            valid = cfg.feed_dir + tag.replace("/", " ")
            if file == valid or file == valid + ".lock":
                break
        else:
            log_func("Deleted extraneous file: %s" % file)
            try:
                os.unlink(file)
            except:
                pass

    for fd in cfg.feeds:
        fpath = cfg.feed_dir + fd.tag.replace("/", " ")
        lpath = fpath + ".lock"

        try:
            lock = os.open(lpath, os.O_CREAT|os.O_EXCL)
        except OSError:
            if time.time() - os.stat(lpath).st_ctime > 120:
                os.unlink(lpath)
                log_func("Deleted stale lock for %s." % fd.tag)
                try:
                    lock = os.open(lpath, os.O_CREAT|os.O_EXCL)
                except:
                    log_func("Failed twice to get lock for %s." % fd.tag)
                    continue
            else:
                log_func("Failed once to get lock for %s." % fd.tag)
                continue
        os.close(lock)

        if os.path.exists(fpath):
            if os.path.isfile(fpath):
                f = open(fpath, "rb")
                try:
                    curfeed = cPickle.load(f)
                except:
                    log_func("cPickle load exception on %s" % fpath)
                    os.unlink(lpath)
                    continue
                f.close()
            else:
                log_func("%s is not normal file, old format?" % fpath)
                log_func("  Deleting...")
                if os.path.isdir(fpath):
                    shutil.rmtree(fpath)
                else:
                    os.unlink(fpath)
                curfeed = emptyfeed
        else:
            curfeed = emptyfeed

        if time.time() - curfeed["canto_update"] < fd.rate * 60 and not force:
            os.unlink(lpath)
            continue
        log_func("Updating %s" % fd.tag)

        newfeed = feedparser.parse(fd.URL)
        if newfeed.has_key("bozo_exception"):
            log_func("Recoverable error in feed %s: %s" % 
                        (fd.tag, newfeed["bozo_exception"]))
            newfeed["bozo_exception"] = None

        newfeed["canto_state"] = curfeed["canto_state"]
        newfeed["canto_update"] = time.time()
        for entry in newfeed["entries"]:
            if entry.has_key("content"):
                for c in entry["content"]:
                    c["value"] = c["value"].encode("UTF-8")
                    c["value"] = c["value"].replace("%", "\\%")

            for key in entry.keys():
                if type(entry[key]) in [unicode,str]:
                    entry[key] = entry[key].encode("UTF-8")
                    entry[key] = entry[key].replace("%", "\\%")

        for entry in newfeed["entries"]:
            if not entry.has_key("id"):
                if entry.has_key("link"):
                    entry["id"] = entry["link"]
                elif entry.has_key("title"):
                    entry["id"] = entry["title"]
                else:
                    entry["id"] = None

            for centry in curfeed["entries"]:
                if entry["id"] == centry["id"]:
                    entry["canto_state"] = centry["canto_state"]
                    curfeed["entries"].remove(centry)
                    break

            if not entry.has_key("canto_state"):
                entry["canto_state"] = [ fd.tag, "unread", "*", "new"]

        
        if len(newfeed["entries"]) < fd.keep:
            newfeed["entries"] += \
                curfeed["entries"][:fd.keep - len(newfeed["entries"])]
        else:
            newfeed["entries"] = newfeed["entries"][:fd.keep]

        f = open(fpath, "wb")
        try:
            cPickle.dump(newfeed, f)
        except:
            log_func("cPickle dump exception on %s" % fpath)
            raise
        f.close()

        os.unlink(lpath)
    
    log_func("Gracefully exiting Canto-fetch.")
    return 0
