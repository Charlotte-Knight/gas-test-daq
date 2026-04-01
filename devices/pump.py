"""
Interface for the vacuum pump.
https://www.idealvac.com/files/manuals/Edwards_nXDS_ScrollPumpManual.pdf
https://highvacdepot.com/wp-content/uploads/2018/03/Edwards-nXDS-Serial-Comms-Interface-Manual.pdf
"""

import serial
import time

class VacuumPump:
    def __init__(self):
        self.ser = ser = serial.Serial(
            port="/dev/ttyUSB1",
            baudrate=9600,
            bytesize=8,
            parity='N',
            stopbits=1,
            timeout=1
        )

    def cmd(self, cmd):
        self.ser.write((cmd + "\r").encode("ascii"))
        return self.ser.readline().decode("ascii").strip()

    def start(self):
        #return "Pump started"
        return self.cmd("!C802 1")

    def stop(self):
        #return "Pump stopped"
        return self.cmd("!C802 0")

    # def speed(self):
    #     return self.cmd("?V802")

    def close(self):
        self.ser.close()

if __name__ == "__main__":
    pump = NXDSPump("/dev/ttyUSB1")
    #print("Starting pump:", pump.start())
    #time.sleep(5)
    print("Stopping pump:", pump.stop())
    pump.close()
