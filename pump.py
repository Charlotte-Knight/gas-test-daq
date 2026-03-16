import serial
import time

class NXDSPump:
    def __init__(self, port):
        self.ser = ser = serial.Serial(
            port=port,
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
        return self.cmd("!C802 1")

    def stop(self):
        return self.cmd("!C802 0")

    # def speed(self):
    #     return self.cmd("?V802")

    def close(self):
        self.ser.close()

if __name__ == "__main__":
    pump = NXDSPump("/dev/ttyUSB1")
    print("Starting pump:", pump.start())
    time.sleep(5)
    print("Stopping pump:", pump.stop())
    pump.close()