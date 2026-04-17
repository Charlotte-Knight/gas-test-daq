import logging
import threading
lock = threading.Lock()

import time

from sqlmodel import Session

from database import engine, get_mode, get_pump
from models import Measurement, PumpState, Mode
from devices import PiraniGauge, PressureGauge, VacuumPump

from collections import deque

# In-memory buffer to hold the latest 100 pressure readings for noise evaluation
buffer = deque(maxlen=100)
# to hold the latest ADC reading for the database thread to access
latest_values = None 

logger = logging.getLogger(__name__)

pressure_gauge = PressureGauge()
pump = VacuumPump()
pirani = PiraniGauge()

class DAQThread(threading.Thread):
    """Base class for DAQ threads that run at a fixed interval."""
    def __init__(self, name: str, interval: float = 1.0) -> None:
        super().__init__(name=name, daemon=True)
        self.name = name
        self.interval = interval
        self._stop_event = threading.Event()

    def stop(self) -> None:
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
        super().__init__(name="DatabaseThread", interval=interval)
    
    def _tick(self) -> None:
        with Session(engine) as session:
            with lock:
                ch1 = latest_values
            
            if ch1 is None:
                logger.debug("No valid ADC readings yet, skipping tick")
                return
            
            mode = get_mode(session)
            pump_state = get_pump(session)
            pirani_pressure = pirani.read_pressure()

            # PLACEHOLDER: need to implement logic to check whether pump already on/off or not
            if pump_state == PumpState.ON:
                pump.start()
            else:
                pump.stop()

            if mode == Mode.DATATAKING:
                measurement = Measurement(
                    ch1=round(ch1, 4),
                    pressure=pressure_gauge.get_pressure_from_voltage(ch1),
                    pirani_pressure=pirani_pressure,
                    mode=mode,
                    pump=pump_state
                )
                session.add(measurement)
                session.commit()

class SamplerThread(DAQThread):
    def __init__(self, interval: float = 1.0) -> None:
        super().__init__(name="SamplerThread", interval=interval)
    
    def _tick(self) -> None:
        global latest_values
        ch1 = pressure_gauge.read_voltage()
        with lock:
            latest_values = ch1
            buffer.append(ch1)
