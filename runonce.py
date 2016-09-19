#!/usr/bin/env python

# This script is totally not for public consumption. Don't complain about
# hardcoded stuffs.

import time
import argparse
import subprocess
import re
import traceback
import os
import uuid
import requests
import math
import sys
from dbiface import *
from github import Github
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.font_manager as font_manager
from matplotlib.ticker import FormatStrFormatter
import numpy as np

def mkreport(results, pullreq, commit, testapps, estimate):
    template="""
# Power profile
```
Pull request    : {pullreq}
Commit hash     : {commit}
TestApps hash   : {testapps}
Estimate mode   : {estimate}
```
Application  |  Avg [mA] | Trials | Time | Norm. Batt. | Graph
---|---|---|---|---|---
"""
    rv = template.format(pullreq=pullreq, commit=commit, testapps=testapps, estimate=estimate)
    for r in results:
        m = r["time"]/60
        s = r["time"]%60
        rv += "%s | %.3f | %d | %dm %ds | %.1f d | %s\n" % (r["app"],r["current"],
                r["runs"],m,s,r["lifetime"],r["report"])
    rv += "\nThe normalised battery life field is the number of days you would expect a device drawing this average current to survive on a 1Ah battery."
    return rv

def genplot(imgid, imgname, subtitle):
    reinit()
    majorFormatter = FormatStrFormatter('%.3f')
    cur.execute("SELECT * FROM report_run_ssq WHERE img=%s AND frac > 0.99",(imgid,))
    x = []
    y = []
    r = cur.fetchone()
    while r != None:
        x.append(float(r[2])*1000)
        y.append(math.log(float(r[4])))
        r = cur.fetchone()
    cur.execute("SELECT * FROM report_run_ssq WHERE img=%s AND frac <= 0.99",(imgid,))
    x2 = []
    y2 = []
    r = cur.fetchone()
    while r != None:
        x2.append(float(r[2])*1000)
        y2.append(math.log(float(r[4])))
        r = cur.fetchone()
    fig, ax = plt.subplots(figsize=(16,10))
    ax.grid(True)
    plt.plot(x,y,"go", label="Full trial completed")
    plt.plot(x2,y2,"r+", label="Trial tripped early")
    start, end = ax.get_xlim()
    ax.xaxis.set_ticks(np.arange(start, end, (end-start)/23.))
    axis_font = {'fontname':'Arial', 'size':'18'}
    title_font = {'fontname':'Arial', 'size':'18'}
    ax.xaxis.set_major_formatter(majorFormatter)
    plt.xlabel("Current [mA]", **axis_font)
    plt.ylabel("ln($\Sigma \Delta V^2)$", **axis_font)
    plt.title("Sum of the deviation from expected voltage squared vs current - low values imply current is correct\n"+subtitle, **title_font)
    leg = plt.legend()
    leg.get_frame().set_facecolor('#FFFFFF')
    plt.show()
    os.makedirs("/srv/oncereports/"+imgname)
    pltfname = "/srv/oncereports/%s/deviance.pdf" % imgname
    plt.savefig(pltfname)
#    subprocess.check_call(["git","add","."])
#    subprocess.check_call(["git","commit","-m","add a report","--author","Power Profiling Bot <profilebot@steelcode.com>"])
#    subprocess.check_call(["git","push"])
    return pltfname

def get_results(pid, imgid):
    reinit()
    try:
        db.commit()
        cur.execute("SELECT COUNT(*) FROM runs WHERE runs.image=%s", (imgid,))
        total_runs = cur.fetchone()[0]
        cur.execute("SELECT current, lifetime FROM report_current WHERE img=%s",(imgid,))
        current, lifetime = cur.fetchone()
    except:
        print "PID was:",pid
        print "IMGID was:",imgid
        print "TR was:",total_runs
        print cur.execute("SELECT current, lifetime FROM report_current WHERE img=%s",(imgid,))
        print cur.fetchone()
        raise
    return float(current), int(total_runs), float(lifetime)


if True:
    try:            
        platform = "hamilton"
        image = "once"
        comment = "once"
        usefast = True
        tbranch = str(uuid.uuid4())
        try:
               os.chdir("/srv/base")
               imgname=image+"_"+str(int(time.time()))
               with open("lastimage","w") as f:
                  f.write(imgname)
               thn = time.time()
               ra = ["python","run.py",
                   "--platform",platform,
                   "--configuration","stock",
                   "--image",imgname,
                   "--comment","foo",
                   "--repository", "bar",
                   "--commit", "baz"]
               if usefast:
                    ra += ["--estimate","True"]
               subprocess.check_call(ra)
               dtime = time.time()-thn
               idents = subprocess.check_output(["python","getident.py",
                   "--platform",platform,
                   "--configuration","stock",
                   "--image",imgname])
               time.sleep(10)
               pid, imgid = idents.splitlines()[0].strip().split()
               pid = int(pid)
               imgid = int(imgid)
               print "done: ", repr(pid), repr(imgid)
               genplot(imgid, imgname, "%s   app=%s%s" % ("url","app", " [ESTIMATE MODE]" if usefast else ""))  
               #get magic values
               current, runs, lifetime = get_results(pid, imgid)
               results.append({"app":"once", "runs":runs, "current":current, "report":"once", "time":dtime, "lifetime":lifetime})
               os.chdir("/srv/base")
        except:
               print traceback.format_exc() 
               raise 
        report = mkreport(results, "title", "commit.sha", "appshash", usefast) 
        print report
    except:
        print traceback.format_exc()
        raise
