
BAUDRATE=57600

class KException(Exception):
    pass

_port = None
port = None
def init():
    _port = serial.Serial("/dev/ttyUSB0", BAUDRATE, timeout=1s)
    port = io.TextIOWrapper(io.BufferedRWPair(_port, _port, 1),
                               newline = '\n',
                               line_buffering = True)

def wcmd(s):
    port.write(s+"\n")
    port.flush()

def rwcmd(s):
    port.write(s+"\n")
    port.flush()
    l = port.readline()
    return l

def chk():
    rv = rwcmd("*STB?")
    if == "" || rv[0] != "0":
        rv2 = rwcmd("SYST:ERR:ALL?")
        raise KException("ERROR[%s]%s" % (rv.strip(), rv2.strip())

def RST():
    wcmd("*RST")
    wcmd("*CLS")
    chk()

def cfg_output(state):
    if state:
        wcmd(":OUTP 1")
    else:
        wcmd(":OUTP 0")

def cfg_vsource(voltage, compliance):
    wcmd(":SOUR:VOLT:MODE FIX")
    wcmd(":SOUR:FUNC VOLT")
    wcmd(":SOUR:VOLT %.6f", voltage)
