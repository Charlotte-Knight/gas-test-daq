"""
DAQ background thread.

Hardware abstraction
--------------------
The `read_adc()` function below is currently a simulator. To use real hardware,
replace its body with your ADC driver calls, for example with an ADS1115:

    import board, busio
    import adafruit_ads1x15.ads1115 as ADS
    from adafruit_ads1x15.analog_in import AnalogIn

    i2c  = busio.I2C(board.SCL, board.SDA)
    ads  = ADS.ADS1115(i2c)
    ch   = [AnalogIn(ads, ADS.P0),
            AnalogIn(ads, ADS.P1),
            AnalogIn(ads, ADS.P2)]

    def read_adc() -> tuple[float, float, float]:
        return ch[0].voltage, ch[1].voltage, ch[2].voltage

Digital outputs
---------------
`set_outputs()` currently just prints. Replace with real GPIO calls:

    import RPi.GPIO as GPIO
    GPIO.setmode(GPIO.BCM)
    OUT1_PIN, OUT2_PIN = 17, 27
    GPIO.setup(OUT1_PIN, GPIO.OUT)
    GPIO.setup(OUT2_PIN, GPIO.OUT)

    def set_outputs(out1: bool, out2: bool) -> None:
        GPIO.output(OUT1_PIN, GPIO.HIGH if out1 else GPIO.LOW)
        GPIO.output(OUT2_PIN, GPIO.HIGH if out2 else GPIO.LOW)
"""

import logging
import math
import random
import threading
lock = threading.Lock()

import time

from sqlmodel import Session

from database import engine, get_mode, get_pump
from models import Measurement, Mode, PumpState
from pump import NXDSPump
from pirani import PiraniGauge

import revpimodio2

from collections import deque

buffer = deque(maxlen=100)
latest_values = None

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Hardware abstraction — replace these two functions for real hardware
# ---------------------------------------------------------------------------
_sim_t = 0.0  # internal time counter for the simulator

rpi = revpimodio2.RevPiModIO(autorefresh=True)
pump = NXDSPump("/dev/ttyUSB1")
pirani = PiraniGauge("/dev/ttyUSB0")

def read_adc() -> float:
    """Return ch1 voltage"""
    ch1 = rpi.io.AnalogInput_1.value / 1000
    return ch1


def get_pressure_from_voltage(voltage: float) -> float:
    """
    Convert voltage reading (in V) from RS 309-725 pressure sensor to pressure in bar.
    
    In testing we found that at atmospheric pressures, the sensor reads ~0V, and otherwise it has a linear response with a slope of about 16/10 bar/V. Some more testing and calibration should be done to confirm this.
    """
    return 1.0 + (16/10) * voltage # to be finalised


# ---------------------------------------------------------------------------
# DAQ loop
# ---------------------------------------------------------------------------

class DAQThread(threading.Thread):
    def __init__(self, name: str, interval: float = 1.0) -> None:
        super().__init__(name=name,  daemon=True)
        self.name = name
        self.interval = interval
        self._stop_event = threading.Event()

    def stop(self) -> None:
        """Signal the thread to exit after its current sleep."""
        self._stop_event.set()

    def run(self) -> None:
        logger.info("%s thread started (interval=%.1fs)", self.name, self.interval)
        while not self._stop_event.is_set():
            start = time.monotonic()
            try:
                self._tick()
            except Exception:
                logger.exception("Error in tick — continuing")

            # Sleep for the remainder of the interval to keep a steady rate
            elapsed = time.monotonic() - start
            sleep_for = max(0.0, self.interval - elapsed)
            self._stop_event.wait(timeout=sleep_for)

        logger.info("%s thread stopped", self.name)

    def _tick(self) -> None:
        pass
    

class DatabaseThread(DAQThread):
    def __init__(self, interval: float = 1.0) -> None:
        super().__init__(name="SamplerThread", interval=interval)
    
    def _tick(self) -> None:
        with Session(engine) as session:
            with lock:
                ch1 = latest_values
            
            if ch1 is None:
                # No valid readings yet — skip this tick
                logger.debug("No valid ADC readings yet, skipping tick")
                return
            
            mode = get_mode(session)
            pump_state = get_pump(session)
            pirani_pressure = pirani.read_pressure()

            if pump_state == PumpState.ON:
                pump.start()
            else:
                pump.stop()

            measurement = Measurement(
                ch1=round(ch1, 4),
                pressure=get_pressure_from_voltage(ch1),
                pirani_pressure=pirani_pressure,
                mode=mode,
                pump=pump_state # Placeholder until pump state is implemented in the database and DAQ loop
            )
            session.add(measurement)
            session.commit()
            logger.debug(
                "Saved: ch1=%.3f mode=%s",
                ch1, mode.value,
            )

class SamplerThread(DAQThread):
    def __init__(self, interval: float = 1.0) -> None:
        super().__init__(name="DatabaseThread", interval=interval)
    
    def _tick(self) -> None:
        global latest_values
        ch1 = read_adc()
        with lock:
            latest_values = ch1
            buffer.append(ch1)
