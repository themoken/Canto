import os
import sys
import parse
import codecs
import time

class Feed :
    def __init__(self, dir_path, handle, URL, rate, keep, log_func):
        self.handle = handle
        self.URL = URL
        self.rate = rate
        self.keep = keep
        self.pf = None
        self.log = log_func
        self.path = dir_path
        self.idx = self.path + "/../" + self.handle + ".idx"

    def search_entries(self, string):
        for s in self.pf:
            if s["title"] == string:
                return 1
        return 0

    def sanitize_path(self, string):
        string = string.replace("/", " ")
        return string

    def update(self):
        self.log("Updating %s\n" % self.handle)
        self.pf = parse.ParsedFeed(self.URL, self.log)
        self.dump_to_files()
        self.log("Dumped.\n")
        idxtmp = self.idx + ".tmp"

        try:
            os.rename(self.idx, idxtmp)
        except: 
            idxtmp = None

        try:
            fsock = codecs.open(self.idx, "w", "UTF-8", "ignore")
            try:
                items = 0
                for s in self.pf:
                    if items >= self.keep and s["title"] not in [x["title"] for x in self.pf[:items + 1]]:
                        str = self.sanitize_path(s["title"])
                        try:
                            os.unlink(self.path + "/" + str)
                        except:
                            pass
                    else:
                        fsock.write(s["title"] + "\00")
                        items += 1
                
                if idxtmp :
                    try:
                        tmpsock = codecs.open(idxtmp, "r", "UTF-8", "ignore")
                        try:
                            lines = tmpsock.read().split("\00")[:-1]
                            for l in lines:
                                if not self.search_entries(l):
                                    if items >= self.keep :
                                        str = self.sanitize_path(l)
                                        os.unlink(self.path + "/" + str)
                                    else:
                                        fsock.write(l + "\00")
                                        items += 1
                        finally :
                            tmpsock.close()
                    except :
                        raise
                    os.unlink(idxtmp)
            finally :
                fsock.close()
        except :
            raise

    def dump_to_files(self):
        for s in self.pf :
            sanpath = self.sanitize_path(s["title"])
            fullpath = self.path + "/" + sanpath
            fullpath = fullpath.encode("utf-8", "ignore")

            try:
                f = os.stat(fullpath)
            except :
                try :
                    fsock = codecs.open(fullpath, "w", "UTF-8", "ignore")
                    try :
                        fsock.write(s["title"] + "\00")
                        fsock.write(s["link"] + "\00")
                        fsock.write(s["description"] + "\00")
                        fsock.write(self.handle + ",*\00")
                    finally :
                        fsock.close()
                except:
                    self.log("%s %s %s\n" % sys.exc_info())

    def tick(self):
        if not os.path.exists(self.idx) or \
                time.time() - os.stat(self.idx).st_mtime > self.rate * 60:
            self.update()
