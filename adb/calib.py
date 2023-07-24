#!/usr/bin/env python3

# high level fuzzer (using adb)

from chipshouter import ChipSHOUTER
import time
import subprocess
import phywhisperer.usb as pw
import sys
phy = pw.Usb()
phy.con(program_fpga=True)
import getopt

buttonState = 0
PULSEWIDTH = 35

print("Initializing chipshouter")
cs = ChipSHOUTER("/dev/ttyUSB0")

cs.voltage.set = 250
time.sleep(0.5)
cs.armed = 1
time.sleep(0.1)


GDATA = b'witch1:6250000\n0:6250000\n1:6250000\n0:6250000\n1:6250000\n0:6250000\n1:6250000\n0:6250000\n1:6250000\n0:6250000\n1:6250000\n0:6250000\n1:6250000\n0:6250000\n1:6250000\n0:6250000\n1:6250000\n0:6250000\n1:6250000\n0:6250000\n1:6250000\n0:6250000\n1:6250000\n0:6250000\n1:6250000\n0:6250000\n1:6250000\n0:6250000\n1:6250000\n0:6250000\n1:6250000\n0:6250000\n1:6250000\n0:6250000\n1:6250000\n0:6250000\n1:6250000\n0:6250000\n1:6250000\n0:6250000\n1:6250000\n0:6250000\n1:6250000\n0:6250000\n1:6250000\n0:6250000\n1:6250000\n0:6250000\n1:6250000\n0:6250000\n'
# GDATA = b'witch1:90000\n0:90000\n1:90000\n0:90000\n1:90000\n'
# GDATA = b'witch222221:400\n0:400\n1:400\n0:400\n1:400\nbonk\n'
# GDATA = b'witch1:20000\n0:20000\n1:20000\n0:20000\n1:20000\nbonk\n'

CFG_COUNT = 200
CFG_PULSE = 45
CFG_DELAY = 425
CFG_QUIET = False
CFG_DELAY_RANGE = 10

def clearGPIO():
  phy.set_power_source("off")
  phy.write_reg(phy.REG_USERIO_DATA,[0])

if __name__ == "__main__":
  if len(sys.argv) == 1:
    print("Please specify something")
    sys.exit(0)
  opts, leftover = getopt.getopt(sys.argv[1:],"qd:c:p:r:",["quiet","delay=","coun=t","pulsewidth=","range="])
  for opt, arg in opts:
    if opt in ["-d","--delay"]:
      CFG_DELAY = int(arg)
    elif opt in ["-c","--count"]:
      CFG_COUNT = int(arg)
    elif opt in ["-r","--range"]:
      CFG_DELAY_RANGE = int(arg)
    elif opt in ["-p","--pulsewidth"]:
      CFG_PULSE = int(arg)
    elif opt in ["-q","--quiet"]:
      CFG_QUIET = True

print("-" * 80)
print(" - CFG_COUNT is %d" % CFG_COUNT)
print(" - CFG_PULSE is %d" % CFG_PULSE)
print(" - CFG_DELAY is %d" % CFG_DELAY)
if CFG_QUIET is True:
  print(" - CFG_QUIET set, oct6 blocker disabled")
print("-" * 80)
sys.stdout.flush()

def togglePin(in_bit):
  global buttonState
  if in_bit >= 7:
    print("error: max is d7")
    return
  buttonState = buttonState ^ (1 << in_bit)
  phy.write_reg(phy.REG_USERIO_DATA,[buttonState])

def testAdb(entryVar=None):
  global GDATA
  proc = None
  try:
    if entryVar is not None:
      proc = subprocess.run(["adb","shell","/data/local/tmp/slimectr","%d" % (entryVar)],capture_output=True,timeout=10);
    else:
      proc = subprocess.run(["adb","shell","/data/local/tmp/slimectr"],capture_output=True,timeout=10);
    time.sleep(2.0)
    stdout = proc.stdout
    stderr = proc.stderr
    print(stdout)
    if stdout is None:
      print("stdout is none, crashed")
      sys.stdout.flush()
      return 0
    elif b'winner' in stdout:
      print("unexpected, winner")
      sys.stdout.flush()
      input(" > winner winner chicken dinner < ")
      return 1
    elif stdout != GDATA:
      print("unexpected - rebooting")
      sys.stdout.flush()
      return 0
    elif stdout == b'witch' or stdout == b'':
      print("needs a reboot")
      return 0
    print("NORMAL OUTPUT")
    print(stderr)
    return 1
  except subprocess.TimeoutExpired as te:
    stdout = te.stdout
    stderr = te.stderr
    print(stdout)
  try:
    proc.kill()
    return 0
  except:
    print("Cannot kill process")
    return 0

def enterADB():
  PIN_RST = 0
  PIN_PWR = 1
  PIN_VOL = 2
  PIN_FET = 3
  print("enterADB: enabling mosfet")
  togglePin(PIN_FET)
  time.sleep(0.25) 
  print("enterADB: holding power") 
  togglePin(PIN_PWR)
  time.sleep(2.5) 
  togglePin(PIN_PWR)
  print("enterADB: power released")
  time.sleep(0.25)
  print("enterADB: You should be in normal boot...")
 
# flashing unlock
capturemask = [0x77,0x69,0x74,0x63,0x68]
# flashing unlock
# capturemask = [0x75,0x6e,0x6c,0x6f,0x63,0x6b]
# usb descriptor
# capturemask = [0x80, 0x06, 0x01, 0x03, 0x00, 0x00,0xFE,0x0F]

def resetFPGA():
  global phy,capturemask
  phy.reset_fpga()
  phy.set_power_source("off")
  phy.write_reg(phy.REG_USERIO_PWDRIVEN,[0xFF])
  phy.write_reg(phy.REG_USERIO_DATA,[0x0])
 
packetPrinter = pw.USBSimplePrintSink(highspeed=False)

c = None
doResetAll = True
import random

glitchCtr = 0
while glitchCtr <= CFG_COUNT:
  glitchCtr += 1
  ret = ""
  PULSEWIDTH = random.randint(CFG_PULSE,CFG_PULSE + 3)
  delay_time = random.randint(CFG_DELAY,CFG_DELAY + CFG_DELAY_RANGE)
  if doResetAll:
    print("[%f] Resetting FPGA state" % delay_time)
    resetFPGA()
  print("[%f] Entering attempt %d" % (delay_time,glitchCtr))
  phy.set_pattern(capturemask,mask=[0xFF for c in capturemask])
  us_delay = 30 + delay_time
  print("True delay: %f + %d countloop, pulse width %d" % (us_delay,delay_time,PULSEWIDTH))
  if doResetAll:
    print("[%f] Resetting device and trying again" % delay_time)
    enterADB()
    time.sleep(0.1)
    phy.set_power_source("host")
    print("Waiting for 20s at 5v power")
    time.sleep(20.0)
  else:
    print("Skipping hard reset")
    time.sleep(1.0)
  if True:
    print("Arming PhyWhisperer")
    phy.set_capture_size(1024)
    phy.set_pattern(capturemask,mask=[0xFF for c in capturemask])
    phy.set_trigger(enable=True,delays=[us_delay],widths=[phy.ns_trigger(PULSEWIDTH)])
    print("ChipSHOUTER Voltage...")
    print(cs.voltage)
    phy.arm()
    print("Testing ADB (delay %d)" % delay_time)
    doResetAll = False
    # rval = testAdb(delay_time)
    rval = testAdb()
    # input(">")
    if rval == 0:
      print("process failed, rebooting")
      doResetAll = True
      print("[%f] Hard powering off device" % delay_time)
      phy.set_power_source("off")
      togglePin(3) # PIN_FET
    else:
      print(rval)
      print("process ok, continuing with 1s sleep")
    time.sleep(1.0)
    sys.stdout.flush()
    print("-" * 80)
    raw = phy.read_capture_data()
    packets = phy.split_packets(raw)
    for packet in packets:
      if len(packet["contents"]) == 3 or len(packet["contents"]) == 1:
        continue
      packetPrinter.handle_usb_packet(ts=packet["timestamp"],buf=bytearray(packet["contents"]),flags=0)
    print("-" * 80)
    sys.stdout.flush()

clearGPIO()
if CFG_QUIET is True:
  print("CFG_QUIET is set, skipping oct6 blocker")
  sys.exit(0)

while True:
  x = input("enter 'quit' to exit (prevent mega fuckups like oct6)")
  if x.rstrip() == "quit":
    cs.armed = 0
    sys.exit(0)
