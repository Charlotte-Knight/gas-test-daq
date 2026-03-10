# DAQ & Control System

A FastAPI + SQLModel application for continuous analogue data acquisition, 
digital output control, and live browser visualisation on a Raspberry Pi.

## Project Structure

```
daq_project/
├── main.py          # FastAPI app, routes, SSE stream, lifespan
├── models.py        # SQLModel table definitions (Measurement, Config, Mode)
├── database.py      # Engine, session factory, init_db, get/set mode
├── daq.py           # Background DAQ thread, ADC reads, mode logic, GPIO
├── templates/
│   └── index.html   # Live dashboard (Chart.js, SSE, mode buttons)
└── requirements.txt
```

## Quick Start

```bash
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000
```

Then open `http://<pi-ip>:8000` in any browser on your network.

## Swapping in Real Hardware

### ADC (ADS1115)
In `daq.py`, replace `read_adc()` with:
```python
import board, busio
import adafruit_ads1x15.ads1115 as ADS
from adafruit_ads1x15.analog_in import AnalogIn

i2c = busio.I2C(board.SCL, board.SDA)
ads = ADS.ADS1115(i2c)
channels = [AnalogIn(ads, ADS.P0), AnalogIn(ads, ADS.P1), AnalogIn(ads, ADS.P2)]

def read_adc() -> tuple[float, float, float]:
    return channels[0].voltage, channels[1].voltage, channels[2].voltage
```

### Digital Outputs
In `daq.py`, replace `set_outputs()` with:
```python
import RPi.GPIO as GPIO
GPIO.setmode(GPIO.BCM)
OUT1_PIN, OUT2_PIN = 17, 27
GPIO.setup([OUT1_PIN, OUT2_PIN], GPIO.OUT)

def set_outputs(out1: bool, out2: bool) -> None:
    GPIO.output(OUT1_PIN, out1)
    GPIO.output(OUT2_PIN, out2)
```

## Adding a New Mode

1. Add the value to `Mode` enum in `models.py`
2. Add a branch in `compute_outputs()` in `daq.py`
3. Add a button in `templates/index.html`

## Exporting Data to Pandas

```python
import pandas as pd
from sqlalchemy import create_engine

engine = create_engine("sqlite:///daq.db")
df = pd.read_sql("SELECT * FROM measurement", engine, parse_dates=["timestamp"])
df = df.set_index("timestamp")

# Filter by mode
auto_df = df[df["mode"] == "AUTO"]

# Export to Parquet for efficient storage
df.to_parquet("measurements.parquet")
```

## API Reference

| Method | Path                  | Description                        |
|--------|-----------------------|------------------------------------|
| GET    | `/`                   | Live dashboard                     |
| GET    | `/mode`               | Get current mode                   |
| POST   | `/mode/{mode}`        | Set mode (AUTO / MANUAL / SAFE)    |
| GET    | `/measurements`       | Last N measurements (default 100)  |
| GET    | `/measurements/latest`| Most recent single measurement     |
| GET    | `/stream`             | SSE live data stream               |
| GET    | `/docs`               | Auto-generated Swagger UI          |
