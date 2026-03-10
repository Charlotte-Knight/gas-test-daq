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
import time

from sqlmodel import Session

from database import engine, get_mode
from models import Measurement, Mode

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Hardware abstraction — replace these two functions for real hardware
# ---------------------------------------------------------------------------
_sim_t = 0.0  # internal time counter for the simulator


def read_adc() -> tuple[float, float, float]:
    """Return (ch1, ch2, ch3) voltages. Currently simulated."""
    global _sim_t
    _sim_t += 0.05
    ch1 = 2.5 + 1.5 * math.sin(_sim_t) + random.gauss(0, 0.02)
    ch2 = 1.8 + 0.8 * math.cos(_sim_t * 0.7) + random.gauss(0, 0.02)
    ch3 = abs(math.sin(_sim_t * 0.3)) * 3.3 + random.gauss(0, 0.02)
    return ch1, ch2, ch3


def set_outputs(out1: bool, out2: bool) -> None:
    """Drive digital output pins. Currently a no-op stub."""
    # GPIO.output(OUT1_PIN, out1)
    # GPIO.output(OUT2_PIN, out2)
    pass


# ---------------------------------------------------------------------------
# Mode logic — add or modify modes here
# ---------------------------------------------------------------------------

# Thresholds used by AUTO mode
AUTO_CH1_THRESHOLD = 2.5
AUTO_CH2_THRESHOLD = 1.8


def compute_outputs(mode: Mode, ch1: float, ch2: float, ch3: float) -> tuple[bool, bool]:
    """
    Return (out1, out2) for the given mode and channel readings.
    Extend this function as your modes grow.
    """
    if mode == Mode.SAFE:
        # All outputs off regardless of readings
        return False, False

    if mode == Mode.MANUAL:
        # Outputs held on; in a real system you might read a manual override
        # flag from the config table or a separate endpoint.
        return True, True

    if mode == Mode.AUTO:
        out1 = ch1 > AUTO_CH1_THRESHOLD
        out2 = ch2 > AUTO_CH2_THRESHOLD
        return out1, out2

    # Fallback — safe default
    return False, False


# ---------------------------------------------------------------------------
# DAQ loop
# ---------------------------------------------------------------------------

class DAQThread(threading.Thread):
    """
    Background thread that samples the ADC, resolves outputs for the current
    mode, drives GPIO, and persists each measurement to SQLite.

    The thread runs as a daemon so it exits automatically when the main
    process shuts down. Call `stop()` for a clean shutdown.
    """

    def __init__(self, interval: float = 1.0) -> None:
        super().__init__(name="daq-thread", daemon=True)
        self.interval = interval
        self._stop_event = threading.Event()

    def stop(self) -> None:
        """Signal the thread to exit after its current sleep."""
        self._stop_event.set()

    def run(self) -> None:
        logger.info("DAQ thread started (interval=%.1fs)", self.interval)
        while not self._stop_event.is_set():
            start = time.monotonic()
            try:
                self._tick()
            except Exception:
                logger.exception("Error in DAQ tick — continuing")

            # Sleep for the remainder of the interval to keep a steady rate
            elapsed = time.monotonic() - start
            sleep_for = max(0.0, self.interval - elapsed)
            self._stop_event.wait(timeout=sleep_for)

        logger.info("DAQ thread stopped")

    def _tick(self) -> None:
        ch1, ch2, ch3 = read_adc()

        with Session(engine) as session:
            mode = get_mode(session)
            out1, out2 = compute_outputs(mode, ch1, ch2, ch3)

            set_outputs(out1, out2)

            measurement = Measurement(
                ch1=round(ch1, 4),
                ch2=round(ch2, 4),
                ch3=round(ch3, 4),
                out1=out1,
                out2=out2,
                mode=mode,
            )
            session.add(measurement)
            session.commit()
            logger.debug(
                "Saved: ch1=%.3f ch2=%.3f ch3=%.3f out1=%s out2=%s mode=%s",
                ch1, ch2, ch3, out1, out2, mode.value,
            )
