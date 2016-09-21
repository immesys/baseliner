#!/usr/bin/env python

# This script is totally not for public consumption. Don't complain about
# hardcoded stuffs.
import shutil
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
app_phrase = "running Apps/([^\s].*)"
estimate_phrase = "use estimate mode"
gh = Github("profilebot", password)
repo = gh.get_repo("hamilton-mote/RIOT-OS")
PRs = repo.get_pulls()
def prc(pr, msg):
    pr.create_issue_comment(msg)
    #print "!!!!PRC!!!!!!: ",msg

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
    os.makedirs("/srv/reports/"+imgname)
    plt.savefig("/srv/reports/%s/deviance.pdf" % imgname)
    os.chdir("/srv/reports/")
    #subprocess.check_call(["git","add","."])
    #subprocess.check_call(["git","commit","-m","add a report","--author","Power Profiling Bot <profilebot@steelcode.com>"])
    #subprocess.check_call(["git","push"])
    headers = subprocess.check_output(["curl","-i","https://git.io","-F","url=https://raw.githubusercontent.com/hamilton-mote/power-reports/master/"+imgname+"/deviance.pdf"])
    shorturl = [x for x in headers.splitlines() if x.startswith("Location:")][0].split(":",1)[1]
    return shorturl

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

torun = []
for pr in PRs:
    print "PR: ", pr.title
    if pr.state != "open":
        print "Skip, state = ",pr.state
    mustrun = True
    fast = False
    app = "bcast_sensor_data"
    for c in pr.get_issue_comments():
        if c.user.login == "profilebot":
            mustrun = False
            fast = False
        if retrigger_phrase in c.body:
            mustrun = True
        if estimate_phrase in c.body:
            fast = True
        mg = re.search(app_phrase, c.body)
        if mg != None:
            app = mg.group(1)
    if mustrun:
        commit = pr.get_commits().reversed[0]
        imagename = pr.title.lower()
        imagename = imagename.replace(" ","_")
        imagename = re.sub("[^a-z0-9_]", "", imagename)
        imagename += "_"+commit.sha[:8]
        torun += [(imagename, commit, pr, fast, app)]

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
        prc(pr,"Ok, I started on this now. It'll take some time to do all the trials, check back later.")
        image = i[0]
        comment = "for @"+pr.user.login
        repository = pr.url
        commit = i[1]
        usefast = i[3]
        app = i[4]
        tbranch = str(uuid.uuid4())
        try:
            print "Configuring repo"
            os.chdir("/srv")
            try:
                shutil.rmtree('/srv/riot')
            except:
                print("could not delete /srv/riot")
            subprocess.check_call(["git","clone","--reference","/srv/os_cache","https://github.com/hamilton-mote/RIOT-OS.git","riot"])
            os.chdir("/srv/riot")
            subprocess.check_call(["git","fetch","--all"])
            subprocess.check_call(["git","fetch","origin","pull/%d/head:T%s" %(pr.number, tbranch)])
            subprocess.check_call(["git","checkout","T"+tbranch])
            # os.chdir("/srv/riot")
            # subprocess.check_call(["git","reset","--hard"])
            # subprocess.check_call(["git","clean", "-dfx"])
            # subprocess.check_call(["git","fetch","--all"])
            # subprocess.check_call(["git","fetch","origin","pull/%d/head:T%s" %(pr.number, tbranch)])
            # preserveCode=False
            # if preserveCode:
            #     subprocess.check_call(["git","checkout","hamilton-support"])
            #     subprocess.check_call(["git","pull"])
            #     subprocess.check_call(["git","checkout","-b","H"+tbranch])
            #     subprocess.check_call(["git","rebase","--onto","T"+tbranch, "master", "H"+tbranch])
            # else:
            #     subprocess.check_call(["git","checkout","T"+tbranch])
            #     subprocess.check_call(["git","merge","hamilton-support","--no-commit"])

        except Exception as e:
            prc(pr, "I could not rebase in the platform support. @immesys, I need human help")
            print traceback.format_exc()
            continue


        try:
            print "Building apps"
            os.chdir("/srv")
            try:
                shutil.rmtree('/srv/apps')
            except:
                print("could not delete /srv/apps")
            subprocess.check_call(["git","clone","--reference","/srv/app_cache","https://github.com/hamilton-mote/Apps.git","apps"])
            os.chdir("/srv/apps")
            appshash = subprocess.check_output(["git","log","-1",'--format="%H"']).strip()[1:-1]
        except:
            prc(pr, "I could not update the profiling apps. @immesys, I need human help")
            print traceback.format_exc()
            continue

        results = []
        os.chdir("/srv/base")
        for k in [app]:#os.listdir("/srv/apps"):
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
               ra = ["python","run.py",
                   "--platform",platform,
                   "--configuration","stock",
                   "--image",imgname,
                   "--comment",comment,
                   "--repository", repository,
                   "--commit", commit.sha]
               if usefast:
                    ra += ["--estimate","True"]
               subprocess.check_call(ra)
               dtime = time.time()-thn
               idents = subprocess.check_output(["python","getident.py",
                   "--platform",platform,
                   "--configuration","stock",
                   "--image",imgname])
               time.sleep(20)
               pid, imgid = idents.splitlines()[0].strip().split()
               pid = int(pid)
               imgid = int(imgid)
               print "done: ", repr(pid), repr(imgid)
               ploturl = genplot(imgid, imgname, "%s   app=%s%s" % (pr.url[28:],k.replace("_","-"), " [ESTIMATE MODE]" if usefast else ""))
               #get magic values
               current, runs, lifetime = get_results(pid, imgid)
               results.append({"app":k, "runs":runs, "current":current, "report":ploturl, "time":dtime, "lifetime":lifetime})
               os.chdir("/srv/base")
            except:
               prc(pr, "I could not build and run %s on this PR, @immesys will check why" % k)
               print traceback.format_exc()
               continue
        if len(results) == 0:
            prc(pr, "There is no report, none of the apps ran correctly")
        else:
            report = mkreport(results, pr.title, commit.sha, appshash, usefast)
            prc(pr, report)
    except:
        prc(pr, "I died while processing this, my bad. @immesys will tend to it shortly")
        print traceback.format_exc()
        continue
