#!/usr/bin/env python3

# high level fuzzer (using adb)

import fastboot
import time
import subprocess
import phywhisperer.usb as pw
import sys
phy = pw.Usb()
phy.con(program_fpga=True)
import geotpt

buttonState = 0
PULSEWIDTH = 35

GDATA = b'witch1:6250000\n0:6250000\n1:6250000\n0:6250000\n1:6250000\n0:6250000\n1:6250000\n0:6250000\n1:6250000\n0:6250000\n1:6250000\n0:6250000\n1:6250000\n0:6250000\n1:6250000\n0:6250000\n1:6250000\n0:6250000\n1:6250000\n0:6250000\n1:6250000\n0:6250000\n1:6250000\n0:6250000\n1:6250000\n0:6250000\n1:6250000\n0:6250000\n1:6250000\n0:6250000\n1:6250000\n0:6250000\n1:6250000\n0:6250000\n1:6250000\n0:6250000\n1:6250000\n0:6250000\n1:6250000\n0:6250000\n1:6250000\n0:6250000\n1:6250000\n0:6250000\n1:6250000\n0:6250000\n1:6250000\n0:6250000\n1:6250000\n0:6250000\n'

CFG_COUNT = 200
CFG_PULSE = 45
CFG_DELAY = 425

if __name__ == "__main__":
  if len(sys.argv) == 1:
    print("Please specify something")
    sys.exit(0)
  opts, leftover = getopt.getopt(sys.argv[1:],"d:c:p:",["delay=","coun=t","pulsewidth="])
  for opt, arg in opts:
    if opt in ["-d","--delay"]:
      CFG_DELAY = int(arg)
    elif opt in ["-c","--count"]:
      CFG_COUNT = int(arg)
    elif opt in ["-p","--pulsewidth"]:
      CFG_PULSE = int(arg)

print("-" * 80)
print(" - CFG_COUNT is %d" % CFG_COUNT)
print(" - CFG_PULSE is %d" % CFG_PULSE)
print(" - CFG_DELAY is %d" % CFG_DELAY)
print("-" * 80)
sys.stdout.flush()

def togglePin(in_bit):
  global buttonState
  if in_bit >= 7:
    print("error: max is d7")
    return
  buttonState = buttonState ^ (1 << in_bit)
  phy.write_reg(phy.REG_USERIO_DATA,[buttonState])

def testAdb():
  global GDATA
  proc = subprocess.run(["adb","shell","/data/local/tmp/slimectr"],capture_output=True,timeout=5000);
  try:
    time.sleep(3.0)
    stdout = proc.stdout
    stderr = proc.stderr
    # stdout,stderr = proc.communicate(timeout=5.0)
    print(stdout)
    if stdout != GDATA and stdout != b'witch' and stdout != b'':
      print("unexpected")
      sys.stdout.flush()
      input(" > unexpected < ")
      # proc.kill()
      return 0
    if stdout == b"witch" or stdout == b"":
      print("needs a reboot")
      # proc.kill()
      return 0
    print(stderr)
    # proc.kill()
    return 1
  except subprocess.TimeoutExpired as te:
    stdout = te.stdout
    stderr = te.stderr
    print(stdout)
  try:
    proc.kill()
    return 0
  except:
    pass

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
  time.sleep(1.5)
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
  PULSEWIDTH = random.randint(CFG_PULSE,CFG_PULSE + 10)
  # base_trigger = phy.us_trigger(16.83)
  # delay_time = 3100 + (glitchCtr // 2)
  delay_time = random.randint(CFG_DELAY,CFG_DELAY + 10)
  if doResetAll:
    print("[%f] Resetting FPGA state" % delay_time)
    resetFPGA()
  print("[%f] Entering attempt %d" % (delay_time,glitchCtr))
  phy.set_pattern(capturemask,mask=[0xFF for c in capturemask])
  us_delay = delay_time
  print("True delay: %f, pulse width %d" % (us_delay,PULSEWIDTH))
  if doResetAll:
    print("[%f] Resetting device and trying again" % delay_time)
    enterADB()
    time.sleep(0.1)
    phy.set_power_source("5V")
    print("Waiting for 20s at 5v power")
    time.sleep(20.0)
  else:
    print("Skipping hard reset")
    time.sleep(1.0)
  if True:
    print("Arming PhyWhisperer")
    phy.set_capture_size(512)
    phy.set_pattern(capturemask,mask=[0xFF for c in capturemask])
    phy.set_trigger(enable=True,delays=[us_delay],widths=[phy.ns_trigger(PULSEWIDTH)])
    phy.arm()
    print("Testing ADB")
    doResetAll = False
    rval = testAdb()
    # input(">")
    if rval == 0:
      print("process failed, rebooting")
      doResetAll = True
      print("[%f] Hard powering off device" % delay_time)
      phy.set_power_source("off")
      togglePin(3) # PIN_FET
    else:
      print("process ok, continuing with 5s sleep")
    time.sleep(5.0)
    sys.stdout.flush()

while True:
  x = input("enter 'quit' to exit (prevent mega fuckups like oct6)")
  if x.rstrip() == "quit":
    sys.exit(0)
