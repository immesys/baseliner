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
parser.add_argument('image', type=str, action='store',
                   help='The name of the image')
parser.add_argument('comment', type=str, action='store',
                   help='Comment')
parser.add_argument('repository', type=str, action='store',
                   help='The repository URL for the code')
parser.add_argument('commit', type=str, action='store',
                   help='The commit hash')
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

#plat = create_platform("hamilton","stock")
plat = load_platform("firestorm","stock")
img = plat.create_image("hamilton_blank_1")
#img = plat.load_image("tinyos_gabe_test","initial1")
s = Scheduler(60,3.0,3.15,3.30,img, skipfine=False)

s.begin()
