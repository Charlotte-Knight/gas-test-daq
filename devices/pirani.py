"""
Interface for the Pirani (low pressure) gauge.
https://uk.my.edwardsvacuum.com/en/GBP/Catalog/Measurement%2C-Leak-Detection-and-Control/Gauge-Indirect-Pressure-Measurement/APG-Series-Pirani-Gauge/nAPG200-Series-%28digital%29/p/D1G2010200
"""

import serial

class PiraniGauge:
    def __init__(self):
        self.ser = ser = serial.Serial(
            port="/dev/ttyUSB0",
            baudrate=9600,
            bytesize=8,
            parity='N',
            stopbits=1,
            timeout=1
        )

    def cmd(self, cmd):
        self.ser.write((cmd + "\r").encode("ascii"))
        return self.ser.readline().decode("ascii").strip()
      
    def read_pressure(self):
        response = self.cmd("?V752")
        if response[0] == "*":
            raise ValueError("Pressure reading from pirani gauge returned error: " + response)
        elif response[0] == "=":
            data = response.split("V752 ")[1].split(";")[0]
            pressure_mbar = float(data)
            return pressure_mbar / 1000.0
        else:
            raise ValueError("Unexpected response from pirani gauge: " + response)

    def close(self):
        self.ser.close()
        
if __name__ == "__main__":
    gauge = PiraniGauge("/dev/ttyUSB0")
    print("Current pressure:", gauge.read_pressure())
    gauge.close()