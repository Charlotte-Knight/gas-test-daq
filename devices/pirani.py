import serial

class PiraniGauge:
    """
    Interface for the Pirani (low pressure) gauge.
    https://uk.my.edwardsvacuum.com/en/GBP/Catalog/Measurement%2C-Leak-Detection-and-Control/Gauge-Indirect-Pressure-Measurement/APG-Series-Pirani-Gauge/nAPG200-Series-%28digital%29/p/D1G2010200
    """
    GAS_TYPE_MAP = {
        "Air": 0,
        "Ar": 1,
        "He": 2,
        "CO2": 3,
        "Ne": 4,
        "Kr": 5,
        "Xe": 6
    }
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
        
    def set_gas_type(self, gas_type):
        if gas_type not in ["Air", "Ar", "He", "CO2", "Ne", "Kr", "Xe"]:
            raise ValueError(f"Unsupported gas type: {gas_type}. Expected one of: Air, Ar, He, CO2, Ne, Kr, Xe")
        gas_code = self.GAS_TYPE_MAP.get(gas_type)
        response = self.cmd(f"!S756 {gas_code}")

        if response.startswith("*S756 00"):
            return
        else:
            raise ValueError(f"Setting gas type failed, instrument returned: {response}")
    
    def do_atmospheric_adjustment(self):
        """
        This function sends the serial command to carry out atmospheric adjustment (calibration).
        
        Instructions from manual:
        1. Supply power to the gauge, make sure that the LED indicator is green and allow the 1.
        gauge to warm up at atmospheric pressure in nitrogen or air for at least 10 minutes.
        2. Initiate the atmosphere adjustment by sending the calibrate command to the
        gauge.
        3. The LED indicator will flash cyan to indicate the operation is being performed.
        4. After 3 seconds, the LED indicator stops flashing and the atmosphere adjustment
        parameters are stored in the gauge.
        5. The status of the gauge during this adjustment is displayed in the gauge status that 5.
        is returned when the gauge pressure is read. The calibration in process bit will be
        cleared when the adjustment is complete.
        6. The output of the gauge will automatically be adjusted to read atmosphere.
        """
        response = self.cmd("!S761 1;1")
        
        if response == "*S761 1;00":
            return
        else:
            raise ValueError(f"Atmospheric adjustment failed, instrument returned: {response}")

    def close(self):
        self.ser.close()
        
if __name__ == "__main__":
    gauge = PiraniGauge()
    print("Current pressure:", gauge.read_pressure())
    gauge.close()