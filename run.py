from dbiface import *
from scheduler import *
from lib2400 import *
import time
import argparse
import subprocess
import re
#comment repo commit
parser = argparse.ArgumentParser(description='Run a power baseline')
parser.add_argument('platform', metavar='P', type=str, action='store',
                   help='The platform to target')
parser.add_argument('configuration', type=str, action='store',
                   help='The platform configuration')
parser.add_argument('image', type=str, action='store',
                   help='The name of the image')
parser.add_argument('comment', type=str, action='store',
                   help='Comment')
parser.add_argument('repository', type=str, action='store',
                   help='The repository URL for the code')
parser.add_argument('commit', type=str, action='store',
                   help='The commit hash')
parser.add_argument('window', type=int, action='store', default=60,
                   help='The length of an evaluation window')
parser.add_argument('vstart', type=float, action='store', default=3.20,
                   help='The start voltage')
parser.add_argument('vmin', type=float, action='store', default=3.00,
                   help='The min voltage trip')
parser.add_argument('vmax', type=float, action='store', default=3.4,
                   help='The max voltage trip')
args = parser.parse_args()

init()
time.sleep(0.1)
try:
    chk()
    time.sleep(0.1)
    chk()
except:
    #These are old errors
    pass

RST()
time.sleep(1)

plat = load_or_create_platform(args.platform, args.configuration
img = plat.load_or_create_image(args.image)
print "IDENTIFIERS:", plat.id, img.id
s = Scheduler(args.window,args.vmin,args.vstart,args.vmax,img, skipfine=False)

s.begin()
