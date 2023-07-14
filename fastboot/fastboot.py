#!/usr/bin/env python3

import usb.core
import usb.util
from usb.control import get_descriptor

class ClingWrap:
  def __init__(self):
    dev = usb.core.find(idVendor=0x1f3a,idProduct=0x1010)
    self.d = dev
    dev.set_configuration()
    cfg = dev.get_active_configuration()
    intf = cfg[(0,0)]
    ep = usb.util.find_descriptor(intf, custom_match = \
        lambda e: \
          usb.util.endpoint_direction(e.bEndpointAddress) == usb.util.ENDPOINT_OUT)
    assert ep is not None
    ep2 = usb.util.find_descriptor(intf, custom_match = \
        lambda e: \
          usb.util.endpoint_direction(e.bEndpointAddress) == usb.util.ENDPOINT_IN)
    assert ep2 is not None
    self.ep = ep
    self.ep2 = ep2   

  def getDescr(self,slp=0.0):
    # return usb.util.get_string(self.d,256,2)
    data2 =  get_descriptor(self.d,0x0FFE,0x03,1)
    out = []
    for d in data2:
      if d == 0x0:
        continue
      else:
        out.append(chr(d))
    data2 = "".join(out)
    P_OUT = "[%f] GREPTHIS: " % slp
    print(P_OUT + data2)
    return data2

  def bulkTransfer(self,msg="oem unlock",slp=0.0):
    self.ep.write(msg)
    data = self.ep2.read(0x100)
    data2 = "".join([chr(x) for x in data])
    print("[%f] GREPTHIS: %s" % (slp,data2))
    return data2
    
if __name__ == "__main__":
  c = ClingWrap()
  print(c.getDescr())
  print(c.bulkTransfer())
