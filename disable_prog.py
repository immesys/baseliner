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

wcmd(":SOUR2:TTL 15")
chk()
time.sleep(0.5)
