from lib2400 import *
from dbiface import *
import time
import math
import random

def reboot_target(vtarget, compl):

    try:
        rwcmd(":FETC?")
        chk()
    except:
        pass
    cfg_output(0)
    cfg_vsource(0, 0.04)
    chk()
    cfg_output(1)
    chk()
    cfg_measure(True, currmax=0.04, nplc=1, avgcount=1)
    chk()
    time.sleep(4)
    (t, v, i, flags) = meas()
    (t, v, i, flags) = meas()
    if len(flags) != 0:
        raise Exception("Got flags on reboot")
    if (v > 0.1):
        print t,v,i
        cfg_output(0)
        raise Exception("Did not drain the target? %f" % v)
    cfg_output(0)
    cfg_isource(compl, vtarget)
    cfg_output(1)

class Scheduler(object):

    def __init__ (self, target_time, v_min, v_start, v_max, img, \
        outside_runs=1, core_runs=5, boot_slack=3, idle_c_compl=0.1, tick=0.15, finesteps=64, skipfine=False, estimate=False):
        self.target_time = target_time
        self.v_min = v_min
        self.v_start = v_start
        self.v_max = v_max
        self.img = img
        self.outside_runs = outside_runs
        self.core_runs = core_runs
        self.boot_slack = boot_slack
        self.idle_c_compl = idle_c_compl
        self.tick = tick
        self.estimate = estimate
        self.skipfine=skipfine
        self.finesteps = finesteps
        wcmd(":SYST:BEEP:STAT 0")

    def begin(self):
        cur = 0.032
        seqno = 0
        if self.estimate:
            self.target_time = 20
        while True:
            frac, res, v = self.do_run(cur, "coarse_%d" % seqno, self.target_time/10., "coarse")
            print ("\033[34;1m [C]> i=%.5fmA frac=%.2f%% res=%s v=%.2f \033[0m" %
                (cur*1000, frac*100,
                "HIGH" if res == 1 else ("LOW" if res == -1 else "INS"), v))
            seqno += 1
            if res >= 0:
                cur /= 2
            else:
                break
            if cur < 0.000004: #known lower bound
                cur = 0.000001
                break
        start = cur*0.9
        end = (cur*2)*1.1
        print "\033[33;1mCOMPLETED COARSE: %.3f < C < %.3f \033[0m" % (start*1000, end*1000)
        if self.estimate:
            subcoursesteps = 16
        else:
            subcoursesteps = 32
        subcoarse = []
        cur = start
        for i in xrange(subcoursesteps):
            frac, res, v = self.do_run(cur, "subcoarse_%d" % seqno, self.target_time/7., "coarse")
            print ("\033[34;1m [S]> i=%.5fmA frac=%.2f%% res=%s v=%.2f \033[0m" %
                (cur*1000, frac*100,
                "HIGH" if res == 1 else ("LOW" if res == -1 else "INS"), v))
            subcoarse += [(cur, frac, res, v)]
            cur += (end-start) / float(subcoursesteps)
            seqno += 1

        startidx = 0
        endidx = len(subcoarse) - 1
        for i in xrange(len(subcoarse)):
            if subcoarse[i][2] == -1:
                startidx = i
            if subcoarse[i][2] == 1:
                endidx = min(endidx, i)

        start = subcoarse[startidx][0]
        end = subcoarse[endidx][0]
        diff = end - start
        start -= diff*0.3
        end += diff*0.3
        start = max(0, start)
        print "\033[33;1mCOMPLETED SUB-COARSE: %.3f < C < %.3f \033[0m" % (start*1000, end*1000)

        seqno=0
        medium = []
        cur = start
        if self.estimate:
            msteps = 12
        else:
            msteps = 32
        #msteps=4
        for i in xrange(msteps):
            frac, res, v = self.do_run(cur, "medium_%d" % seqno, self.target_time/3., "medium")
            print ("\033[34;1m [M]> i=%.3fmA frac=%.2f%% res=%s v=%.2f \033[0m" %
                (cur*1000, frac*100,
                "HIGH" if res == 1 else ("LOW" if res == -1 else "INS"), v))
            medium += [(cur, frac, res, v)]
            cur += (end-start) / float(msteps)
            seqno += 1


        # print "MEDIUM RESULTS: "
        # print "----------------"
        # for i in medium:
        #     print ("i=%.3fmA frac=%.2f%% res=%s v=%.2f" %
        #         (i[0]*1000, i[1]*100,
        #         "HIGH" if i[2] == 1 else ("LOW" if i[2] == -1 else "INS"), i[3]))

        if self.skipfine:
            cfg_output(0)
            return
        #Now to do fine
        startidx = 0
        endidx = len(medium) - 1
        for i in xrange(len(medium)):
            if medium[i][2] == -1:
                startidx = i
            if medium[i][2] == 1:
                endidx = min(endidx, i)


        start = medium[startidx][0]
        end = medium[endidx][0]
        diff = end - start
        start -= diff*0.3
        end += diff*0.3
        start = max(0, start)
        print "\033[33;1mCOMPLETED MEDIUM: %.3f < C < %.3f \033[0m" % (start*1000, end*1000)
        #print "Medium determination: %.3f < current < %.3f" % (start*1000, end*1000)
        if not self.estimate:
            steps = self.finesteps
        else:
            steps = 16
        delta = (end-start)/float(steps)
        nruns = 1 if self.estimate else self.core_runs
        tests = [start + i*delta for i in xrange(steps)] * nruns
        #This should help disperse real-world time-varying factors like temperature
        random.shuffle(tests)
        for idx in xrange(len(tests)):
            cur = tests[idx]
            frac, res, v = self.do_run(cur, "fine_%d" % idx, self.target_time, "fine")
            print ("\033[34;1m [F %d/%d]> i=%.3fmA frac=%.2f%% res=%s v=%.2f \033[0m" %
                (idx+1,len(tests), cur*1000, frac*100,
                "HIGH" if res == 1 else ("LOW" if res == -1 else "INS"), v))
        print "\033[33;1mCOMPLETED FINE\033[0m"



    def do_run(self, current, comment, target_time, stage):
        run = self.img.create_run(comment, target_time, current, self.v_start, self.v_max, self.v_min, stage)
        reboot_target(self.v_start, self.idle_c_compl)
        time.sleep(self.boot_slack)
        cfg_measure(False, voltmax=self.v_max, nplc=1, avgcount=1)
        meas()
        time.sleep(3)
        reset_time()
        adj_isource(current, self.v_start)
        (t, v, i, flags) = meas()
        run.log_probe(i, v, t/target_time, t)
        adj_isource(current, self.v_max)
        (t, v, i, flags) = meas()
        run.log_probe(i, v, t/target_time, t)
        chk()
        while True:
            (t, v, i, flags) = meas()
            print "\033[36;1m T=%.3f V=%.3f FL=%s" % (t, v, repr(flags))
            #print "got: ", t, v, i, flags
            if (t >= target_time):
                break
            if "CMPL" in flags or v >= self.v_max:
                break
            if v <= self.v_min:
                break
            if len(flags) > 0:
                raise Exception("Unexpected flags: "+repr(flags))
            run.log_probe(i, v, t/target_time, t)
            chk()
            time.sleep(self.tick)
        frac = min(1.0, t/target_time)
        run.log_probe(i, v, frac, t)
        cfg_vsource(0, 0.02)
        if "CMPL" in flags or v >= self.v_max:
            run.log_result(frac, t, v, +1)
            #wcmd(":SYST:BEEP:STAT 1")
            #wcmd(":SYST:BEEP 800, 0.1")
            #time.sleep(0.1)
            #wcmd(":SYST:BEEP 1200, 0.1")
            #time.sleep(0.2)
            #wcmd(":SYST:BEEP:STAT 0")
            return frac,+1, v
        elif v <= self.v_min:
            run.log_result(frac, t, v, -1)
            #wcmd(":SYST:BEEP:STAT 1")
            #wcmd(":SYST:BEEP 800, 0.1")
            #time.sleep(0.1)
            #wcmd(":SYST:BEEP 600, 0.1")
            #time.sleep(0.2)
            #wcmd(":SYST:BEEP:STAT 0")
            return frac,-1, v
        else:
            run.log_result(frac, t, v, 0)
            #wcmd(":SYST:BEEP:STAT 1")
            #wcmd(":SYST:BEEP 800, 0.1")
            #time.sleep(0.1)
            #wcmd(":SYST:BEEP 800, 0.1")
            #time.sleep(0.2)
            #wcmd(":SYST:BEEP:STAT 0")
            return frac,0, v
