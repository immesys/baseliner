#!/usr/bin/env bash
while true
do
    date
    echo "Starting a run"
    rm lastimage
    annotate-output '+^[[33;1m%F_%X^[[0m' python runbot.py | ansi2html > lastlog
    if [ -e lastimage ]
    then    
        cp lastlog /srv/reports/$(cat lastimage)/log.html
        pushd /srv/reports/
        git add .
        git commit -m "Add report for $(cat lastimage)" --author "Power Profiling Bot <profilebot@steelcode.com>"
        git push origin master
        popd
    else
        echo "No image produced, not pushing report to git"
    fi
    date
    sleep 60
done
