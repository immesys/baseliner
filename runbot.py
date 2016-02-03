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
password = os.environ["PROFILEBOTPW"]
retrigger_phrase = "@profilebot please recheck this"
gh = Github("profilebot", password)
repo = gh.get_repo("PowerProfiler/RIOT")
PRs = repo.get_pulls()

def mkreport(results, pullreq, commit, testapps):
    template="""
# Power profile
```
Pull request    : {pullreq}
Commit hash     : {commit}
TestApps hash   : {testapps}
```
Application  |  Avg [mA] | Trials | Time | Norm. Batt. | Graph
---|---|---|---|---|---
"""
    rv = template.format(pullreq=pullreq, commit=commit, testapps=testapps)
    for r in results:
        m = r["time"]/60
        s = r["time"]%60
        rv += "%s | %.3f | %d | %dm %ds | %.1f d | %s\n" % (r["app"],r["current"],
                r["runs"],m,s,r["lifetime"],r["report"])
    rv += "\nThe normalised battery life field is the number of days you would expect a device drawing this average current to survive on a 1Ah battery."
    return rv

def genplot(imgid, imgname, subtitle):
    majorFormatter = FormatStrFormatter('%.3f')
    cur.execute("SELECT * FROM report_run_ssq WHERE img=%s",(imgid,))
    x = []
    y = []
    r = cur.fetchone()
    while r != None:
        x.append(float(r[2])*1000)
        y.append(math.log(float(r[4])))
        r = cur.fetchone()
    fig, ax = plt.subplots(figsize=(16,10))
    ax.grid(True)
    plt.plot(x,y,"b+")
    start, end = ax.get_xlim()
    ax.xaxis.set_ticks(np.arange(start, end, (end-start)/26.))
    axis_font = {'fontname':'Arial', 'size':'18'}
    title_font = {'fontname':'Arial', 'size':'18'}
    ax.xaxis.set_major_formatter(majorFormatter)
    plt.xlabel("Current [mA]", **axis_font)
    plt.ylabel("ln($\Sigma \Delta V^2)$", **axis_font)
    plt.title("Sum of the deviation from expected voltage squared vs current - low values imply current is correct\n"+subtitle, **title_font)
    plt.show()
    os.makedirs("/srv/reports/"+imgname)
    plt.savefig("/srv/reports/%s/deviance.pdf" % imgname)
    os.chdir("/srv/reports/")
#    subprocess.check_call(["git","add","."])
#    subprocess.check_call(["git","commit","-m","add a report","--author","Power Profiling Bot <profilebot@steelcode.com>"])
#    subprocess.check_call(["git","push"])
    headers = subprocess.check_output(["curl","-i","https://git.io","-F","url=https://raw.githubusercontent.com/PowerProfiler/reports/master/"+imgname+"/deviance.pdf"])
    shorturl = [x for x in headers.splitlines() if x.startswith("Location:")][0].split(":",1)[1]
    return shorturl

def get_results(pid, imgid):
    cur.execute("SELECT COUNT(*) FROM runs WHERE runs.image=%s", (imgid,))
    total_runs = cur.fetchone()[0]
    cur.execute("SELECT current, lifetime FROM report_current WHERE img=%s",(imgid,))
    current, lifetime = cur.fetchone()
    return current, total_runs, lifetime

torun = []
for pr in PRs:
    print "PR: ", pr.title
    if pr.state != "open":
        print "Skip, state = ",pr.state
    mustrun = True
    for c in pr.get_issue_comments():
        if c.user.login == "profilebot":
            mustrun = False
        if c.user.login == "immesys" and retrigger_phrase in c.body:
            mustrun = True
    if mustrun:
        commit = pr.get_commits().reversed[0]
        imagename = pr.title.lower()
        imagename = imagename.replace(" ","_")
        imagename = re.sub("[^a-z0-9_]", "", imagename)
        imagename += "_"+commit.sha[:8]
        torun += [(imagename, commit, pr)]

if len(torun) == 0:
    print "No PRs to run"
    sys.exit(13)

# I changed my mind, only do one pull request per invocation of the program
torun = torun[:1]
print "We are processing PR: ",torun[0][0]

for i in torun:
    try:            
        platform = "hamilton"
        pr = i[2]
        pr.create_issue_comment("Ok, I started on this now. It'll take some time to do all the trials, check back later.")
        image = i[0]
        comment = "for @"+pr.user.login
        repository = pr.url
        commit = i[1]
        tbranch = str(uuid.uuid4())
        try:
            print "Configuring repo"
            os.chdir("/srv/riot")
            subprocess.check_call(["git","reset","--hard"])
            subprocess.check_call(["git","clean", "-dfx"])
            subprocess.check_call(["git","fetch","--all"])
            subprocess.check_call(["git","fetch","origin","pull/%d/head:T%s" %(pr.number, tbranch)])
            subprocess.check_call(["git","checkout","hamilton-support"])
            subprocess.check_call(["git","pull"])
            subprocess.check_call(["git","checkout","-b","H"+tbranch])
            subprocess.check_call(["git","rebase","--onto","T"+tbranch, "master", "H"+tbranch])
        except Exception as e:
            pr.create_issue_comment("I could not rebase in the platform support. @immesys, I need human help")
            print traceback.format_exc()
            continue

        
        try:
            print "Building apps"
            os.chdir("/srv/apps")
            subprocess.check_call(["git","reset","--hard"])
            subprocess.check_call(["git","clean", "-dfx"])
            subprocess.check_call(["git","fetch","--all"])
            subprocess.check_call(["git","pull"])
            appshash = subprocess.check_output(["git","log","-1",'--format="%H"']).strip()[1:-1]
        except:
            pr.create_issue_comment("I could not update the profiling apps. @immesys, I need human help")
            print traceback.format_exc()
            continue

        results = []
        os.chdir("/srv/base")
        for k in os.listdir("/srv/apps"):
            try:
               print "\033[43;33;1mRunning application: %s\033[0m" % k
               if not os.path.isdir("/srv/apps/"+k):
                   print "skipping",k
                   continue
               if k[0] == ".":
                   continue
               print "Found app: ", k
               os.chdir("/srv/base/")
               subprocess.check_call(["python","enable_prog.py"])
               os.chdir("/srv/apps/"+k)
               subprocess.check_call(["make","flash"])
               os.chdir("/srv/base")
               subprocess.check_call(["python","disable_prog.py"])
               thn = time.time()
               imgname=image+"_"+k+"_"+str(int(time.time()))
               with open("lastimage","w") as f:
                  f.write(imgname)
               subprocess.check_call(["python","run.py",
                   "--platform",platform,
                   "--configuration","stock",
                   "--image",imgname,
                   "--comment",comment,
                   "--repository", repository,
                   "--commit", commit.sha])
               dtime = time.time()-thn
               idents = subprocess.check_output(["python","getident.py",
                   "--platform",platform,
                   "--configuration","stock",
                   "--image",image+"_"+k])
               pid, imgid = idents.splitlines()[0].strip().split()
               pid, imgid = int(pid), int(imgid)
               print "done: ", pid, imgid
               ploturl = genplot(imgid, imgname, "%s app=%s" % (pr.url,k))  
               #get magic values
               current, runs, lifetime = get_results(pid, imgid)
               results.append({"app":k, "runs":runs, "current":current, "report":ploturl, "time":dtime, "lifetime":lifetime})
               os.chdir("/srv/base")
            except:
               pr.create_issue_comment("I could not build and run %s on this PR, @immesys will check why" % k) 
               print traceback.format_exc() 
               continue
        if len(results) == 0:
            pr.create_issue_comment("There is no report, none of the apps ran correctly")
        else:
            report = mkreport(results, pr.title, commit.sha, appshash) 
            pr.create_issue_comment(report)
    except:
        pr.create_issue_comment("I died while processing this, my bad. @immesys will tend to it shortly")
        print traceback.format_exc()
        continue
