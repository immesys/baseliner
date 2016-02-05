import MySQLdb
from warnings import filterwarnings
filterwarnings('ignore', category = MySQLdb.Warning)
import os

with open("db.conf","r") as f:
    db_user, db_pass, db_host = f.readline().strip().split(";")

db = MySQLdb.connect(host=db_host, user=db_user, passwd=db_pass, db="baseliner")
cur = db.cursor()

class Run(object):
    def __init__(self, runid):
        self.runid = runid
        self.probeseq = 0

    def log_probe(self, current, voltage, runfrac, time):
        cur.execute("""INSERT INTO probe (seqnum, voltage, runfraction, run, time) VALUES
                        (%s, %s, %s, %s, %s)""", (self.probeseq, voltage, runfrac, self.runid, time))
        self.probeseq += 1
        db.commit()

    def log_result(self, frac, time, voltage, result):
        cur.execute("""INSERT INTO runreport (frac, time, voltage, result, run) VALUES
                        (%s, %s, %s, %s, %s)""", (frac, time, voltage, result, self.runid))
        db.commit()

class Image(object):
    def __init__(self, imageid):
        self.id = imageid

    def create_run(self, comment, target_time, current, start_voltage, high_voltage, low_voltage, stage):
        cur.execute("""INSERT INTO runs (comment, image, current, target_time, start_voltage, high_voltage, low_voltage, stage) VALUES
                        (%s, %s, %s, %s, %s, %s, %s, %s)""", (comment, self.id, current, target_time, start_voltage, high_voltage, low_voltage, stage))
        cur.execute("""SELECT LAST_INSERT_ID()""")
        rv = cur.fetchone()
        runid = rv[0]
        db.commit()
        return Run(runid)

class Platform(object):

    def __init__(self, platformid):
        self.id = platformid

    def load_image(self, appname):
        cur.execute("""SELECT idimages FROM images WHERE appname=%s AND target_platform=%s""", (appname, self.id))
        rv = cur.fetchone()
        if rv == None:
            return None
        return Image(rv[0])

    def create_image(self, appname, comment="", repository=None, commit=None):
        if self.load_image(appname) != None:
            raise Exception("Image already exists")
        cur.execute("""INSERT INTO images (appname, comment, repository, commit, target_platform) VALUES
                        (%s, %s, %s, %s, %s)""", (appname, comment, repository, commit, self.id))
        db.commit()
        return self.load_image(appname)
    
    def create_or_load_image(self, appname, comment="", repository=None, commit=None):
        i = self.load_image(appname)
        if i is not None:
            return i
        return self.create_image(appname, comment, repository, commit)

def load_platform(base, configuration):
    cur.execute("""SELECT idplatforms FROM platforms WHERE base=%s AND configuration=%s""", (base, configuration))
    rv = cur.fetchone()
    if rv == None:
        return None
    return Platform(rv[0])

def create_platform(base, configuration):
    p = load_platform(base, configuration)
    if p != None:
        raise Exception("Platform already exists")
    cur.execute("""INSERT INTO platforms (base, configuration) VALUES (%s, %s)""", (base, configuration))
    db.commit()
    return load_platform(base, configuration)

def create_or_load_platform(base, configuration):
    p = load_platform(base, configuration)
    if p is not None:
        return p
    else:
        return create_platform(base, configuration)


