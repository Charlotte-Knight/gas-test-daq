import time
import random
import threading
from database import insert_measurement

current_run_id = None
pump_state = 0

def set_run(run_id):
    global current_run_id
    current_run_id = run_id

def set_pump(state):
    global pump_state
    pump_state = state

def read_pressures():
    # Replace with RevPi readings later
    return (
        2.0 + random.random(),
        3.0 + random.random(),
        4.0 + random.random()
    )

def loop():
    global current_run_id, pump_state

    while True:
        if current_run_id:
            p1, p2, p3 = read_pressures()

            insert_measurement((
                time.time(),
                current_run_id,
                p1,
                p2,
                p3,
                pump_state
            ))

        time.sleep(1)

def start():
    thread = threading.Thread(target=loop, daemon=True)
    thread.start()
