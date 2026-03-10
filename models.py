from datetime import datetime
from enum import Enum
from typing import Optional

from sqlmodel import Field, SQLModel


class Mode(str, Enum):
    AUTO = "AUTO"
    MANUAL = "MANUAL"
    SAFE = "SAFE"


class Measurement(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    timestamp: datetime = Field(default_factory=datetime.utcnow, index=True)
    ch1: float
    ch2: float
    ch3: float
    out1: bool
    out2: bool
    mode: Mode

    class Config:
        # Allows pandas-friendly CSV/parquet export via:
        #   pd.read_sql("SELECT * FROM measurement", engine)
        pass


class Config(SQLModel, table=True):
    key: str = Field(primary_key=True)
    value: str
