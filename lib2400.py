import serial
import io

BAUDRATE=57600

class KException(Exception):
    pass

_port = None
port = None
def init():
    global _port
    global port

    _port = serial.Serial("/dev/ttyUSB0", BAUDRATE, timeout=1)
    port = io.TextIOWrapper(io.BufferedRWPair(_port, _port, 1),
                               newline = '\n',
                               encoding = "ascii",
                               errors = "ignore",
                               line_buffering = True)
    _port.read(1000)

def wcmd(s):
    port.write(unicode(s+"\n"))
    port.flush()

def rline():
    l = port.readline()
    return l

def rwcmd(s):
    port.write(unicode(s+"\n"))
    port.flush()
    l = port.readline()
    return l

def chk():
    rv = rwcmd("*STB?")
    #Not sure what causes this yet
    if rv.strip() == "16":
        rv = rwcmd("*STB?")
    if rv == "" or rv[0] != "0":
        rv2 = rwcmd("SYST:ERR:ALL?")
        raise KException("ERROR[%s]%s" % (rv.strip(), rv2.strip()))

def RST():
    rline()
    wcmd("*RST")
    wcmd("*CLS")
    chk()

def cfg_output(state):
    if state:
        wcmd(":OUTP 1")
    else:
        wcmd(":OUTP 0")

def cfg_vsource(voltage, compliance):
    chk()
    wcmd(":SOUR:VOLT:MODE FIX")
    wcmd(":SOUR:FUNC VOLT")
    wcmd(":SENS:FUNC:CONC 1")
    chk()
    wcmd(':FUNC "VOLT","CURR"')
    wcmd(':CURR:PROT %.9f' % compliance)
    wcmd(":SOUR:VOLT %.9f" % voltage)
    chk()

def cfg_isource(current, compliance):
    wcmd(":SOUR:CURR:MODE FIX")
    wcmd(":SOUR:FUNC CURR")
    wcmd(":SENS:FUNC:CONC 1")
    chk()
    wcmd(':FUNC "VOLT","CURR"')
    wcmd(':VOLT:PROT %.9f' % compliance)
    wcmd(":SOUR:CURR %.9f" % current)
    chk()

def adj_isource(current, compliance):
    wcmd(':VOLT:PROT %.9f' % compliance)
    wcmd(":SOUR:CURR %.9f" % current)
    chk()

def cfg_measure(filt, voltmax=None, currmax=None, nplc=1, avgcount=1):
    if currmax is not None:
        wcmd(":CURR:RANG %.9f" % currmax)
        chk()
    if voltmax is not None:
        wcmd(":VOLT:RANG %.9f" % voltmax)
        chk()
    if filt:
        wcmd(":CURR:NPLC %.2f" % nplc)
        wcmd(":VOLT:NPLC %.2f" % nplc)
        chk()
        wcmd(":AVER:TCON MOV")
        wcmd(":AVER:COUN %d" % avgcount)
        wcmd(":AVER 1")
        chk()
    else:
        wcmd(":CURR:NPLC %.2f" % nplc)
        wcmd(":VOLT:NPLC %.2f" % nplc)
        wcmd(":AVER 0")
        chk()

def reset_time():
    wcmd(":SYST:TIME:RES")

def meas():
    l = rwcmd(":READ?")
    chk()
    v, i, _, t, s = l.split(",")
    v = float(v)
    i = float(i)
    t = float(t)
    s = int(float(s))
    flags = []
    if s & (1<<3):
        flags += ["CMPL"]
    if s & (1<<4):
        flags += ["OVP"]
    if s & (1<<16):
        flags += ["RCMPL"]
    return (t, v, i, flags)
