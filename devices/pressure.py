import revpimodio2
import numpy as np
import time

class PressureGauge:
  """
  Interface for the high pressure (up to 16 bar) gauge.
  https://uk.rs-online.com/web/p/pressure-sensors/0309725
  """
  def __init__(self):
    self.rpi = revpimodio2.RevPiModIO(autorefresh=True)
    
  def read_voltage(self) -> float:
    #ch1 = self.rpi.io.AnalogInput_1.value / 1000 # Convert mV to V
    ch1 = np.sin(time.time()/600) * 10 + 0.5 # Simulate a pressure reading that oscillates between 0 and 
    return ch1
  
  def get_pressure_from_voltage(self, voltage: float) -> float:
    """
    In testing we found that at atmospheric pressures, the sensor reads ~0V, and otherwise it has a linear response with a slope of about 16/10 bar/V. Some more testing and calibration should be done to confirm this.
    """
    return 1.0 + (16/10) * voltage # to be finalised
  
  def read_pressure(self) -> float:
    voltage = self.read_voltage()
    return self.get_pressure_from_voltage(voltage)

if __name__ == "__main__":
    gauge = PressureGauge()
    print(gauge.read_pressure())
