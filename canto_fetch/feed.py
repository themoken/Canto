import os
import sys
import parse
import codecs
import time

class Feed :
    def __init__(self, dir_path, handle, URL, rate, keep, log_func, verbose, force, title_key):
        self.handle = handle
        self.URL = URL
        self.rate = rate
        self.keep = keep
        self.pf = None
        self.log = log_func
        self.verbose = verbose
        self.force = force
        self.path = dir_path
        self.title_key = title_key
        self.idx = self.path + "/../" + self.handle.replace("/", " ") + ".idx"

    def search_entries(self, string):
        for s in self.pf:
            if s["title"] + " " + str(s["hash"]) == string:
                return 1
        return 0

    def sanitize_path(self, string):
        string = string.replace("/", " ")
        return string

    def update(self):
        self.log("Updating %s\n" % self.handle)
        if self.verbose:
            print "Updating %s" % self.handle

        self.pf = parse.ParsedFeed(self.URL, self.log, self.title_key)
        self.dump_to_files()
        idxtmp = self.idx + ".tmp"

        try:
            os.rename(self.idx, idxtmp)
        except: 
            idxtmp = None

        try:
            fsock = codecs.open(self.idx, "w", "UTF-8", "ignore")
            items = 0
            for s in self.pf:
                if items >= self.keep:
                    st = self.sanitize_path(s["title"] + " " + str(s["hash"]))
                    os.unlink(self.path + "/" + st)
                else:
                    fsock.write(s["title"] + " " + str(s["hash"]) + "\00")
                    items += 1
            
            if idxtmp :
                tmpsock = codecs.open(idxtmp, "r", "UTF-8", "ignore")
                lines = tmpsock.read().split("\00")[:-1]
                tmpsock.close()

                for l in lines:
                    if not self.search_entries(l):
                        if items >= self.keep :
                            st = self.sanitize_path(l)
                            os.unlink(self.path + "/" + st)
                        else:
                            fsock.write(l + "\00")
                            items += 1
                os.unlink(idxtmp)
            fsock.close()
        except :
            self.log("%s %s %s\n" % sys.exc_info())
            raise

    def dump_to_files(self):
        for s in self.pf:
            sanpath = self.sanitize_path(s["title"] + " " + str(s["hash"]))
            fullpath = self.path + "/" + sanpath
            fullpath = fullpath.encode("utf-8", "ignore")

            if os.path.exists(fullpath):
                continue

            try:
                fsock = codecs.open(fullpath, "w", "UTF-8", "ignore")
                fsock.write(s["title"] + "\00")
                fsock.write(s["link"] + "\00")
                fsock.write(s["description"] + "\00")
                fsock.write(self.handle + ",*\00")
                fsock.close()
            except:
                self.log("%s %s %s\n" % sys.exc_info())
                raise

    def tick(self):
        if not os.path.exists(self.idx) or \
                time.time() - os.stat(self.idx).st_mtime > self.rate * 60 or\
                self.force :
            self.update()
