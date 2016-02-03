from lib2400 import *
import time

init()
time.sleep(0.1)
try:
    chk()
    time.sleep(0.1)
    chk()
except:
    #These are old errors
    pass

cfg_vsource(3.3,0.1)
cfg_measure(False,currmax=0.1)
cfg_output(1)
time.sleep(2)
wcmd(":SOUR2:TTL 0")
chk()
time.sleep(0.5)
