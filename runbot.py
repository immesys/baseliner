#!/usr/bin/env python

# This script is totally not for public consumption. Don't complain about
# hardcoded stuffs.

import time
import argparse
import subprocess
import re
from github import Github

password = os.environ["PROFILEBOTPW"]
retrigger_phrase = "@profilebot please recheck this"
gh = Github("profilebot", password)
repo = gh.get_repo("PowerProfiler/RIOT")
PRs = repo.get_pulls()

torun = []
for pr in PRs:
    print "PR: ", pr.title
    if pr.state != "open":
        print "Skip, state = ",pr.state
    mustrun = True
    for c in pr.get_issue_comments():
        print "PRc: ", c.user, c.body
        if c.user.login == "profilebot":
            mustrun = False
        if c.user.login == "immesys" and retrigger_phrase in c.body:
            mustrun = True
    if mustrun:
        commit = pr.get_commits()[-1]
        imagename = pr.title.lower()
        imagename = imagename.replace(" ","_")
        imagename = re.sub("[^a-z0-9_]", "", imagename)
        imagename += "_"+commit.sha[:8]
        torun += [(imagename, commit, pr)]

print "We are going to evaluate %d pull requests" % len(torun)
for i in torun:
    print i[0]
print "."

for i in torun:
    platform = "hamilton"
    pr = i[2]
    image = i[0]
    comment = "for @"+pr.user.login
    repository = pr.url
    commit = i[1]
    try:
        print "Configuring repo"
        os.chdir("/srv/riot")
        subprocess.check_call(["git","reset","--hard"])
        subprocess.check_call(["git","clean", "-dfx"])
        subprocess.check_call(["git","fetch","--all"])
        subprocess.check_call(["git","checkout",commit])
        subprocess.check_call(["git","merge","hamilton-support"])
    except:
        pr.create_issue_comment("I could not merge the platform support. @immesys, I need human help")
        continue

    testapps = []
    try:
        print "Building apps"
        os.chdir("/srv/apps")
        subprocess.check_call(["git","reset","--hard"])
        subprocess.check_call(["git","clean", "-dfx"])
        subprocess.check_call(["git","fetch","--all"])
        subprocess.check_call(["git","checkout", "HEAD"])
    except:
        pr.create_issue_comment("I could not update the profiling apps. @immesys, I need human help")
        continue

    os.chdir("/srv/base")
    for k in os.listdir("/srv/apps")
        if not os.path.isdir(k):
            continue
        print "Found app: ", k
        subprocess.check_call(["python","enable_prog.py"])
        os.chdir("/srv/apps/"+k)
        subprocess.check_call(["make","flash"])
        os.chdir("/srv/base")
        subprocess.check_call(["python","disable_prog.py"])
        subprocess.check_call(["python","run.py",
            "--platform",platform,
            "--configuration","stock",
            "--image",image+"_"+k,
            "--comment",comment,
            "--repository", repository,
            "--commit", commit])
        idents = subprocess.check_output(["python","getident.py",
            "--platform",platform,
            "--configuration","stock",
            "--image",image+"_"+k])
        pid, imgid = idents[0].strip().split()
        pid, imgid = int(pid), int(imgid)
        print "done: ", pid, imgid
