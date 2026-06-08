from datetime import datetime

from sqlmodel import Session, SQLModel, create_engine, select

from models import Config, Mode, PumpState, Run

DATABASE_URL = "sqlite:///daq.db"

# check_same_thread=False is required for SQLite when accessed from
# multiple threads (DAQ thread + FastAPI request handlers).
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    echo=False,
)


def init_db() -> None:
    """Create all tables and seed default config values."""
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        # Only insert default mode if the config table is empty
        existing = session.exec(select(Config).where(Config.key == "mode")).first()
        if not existing:
            session.add(Config(key="mode", value=Mode.IDLE.value))
            session.commit()
            
        existing = session.exec(select(Config).where(Config.key == "pump")).first()
        if not existing:
            session.add(Config(key="pump", value=PumpState.OFF.value))
            session.commit()


def get_session() -> Session:
    with Session(engine) as session:
        yield session


def get_mode(session: Session) -> Mode:
    config = session.exec(select(Config).where(Config.key == "mode")).one()
    return Mode(config.value)


def set_mode(session: Session, mode: Mode) -> None:
    config = session.exec(select(Config).where(Config.key == "mode")).one()
    config.value = mode.value
    session.add(config)
    session.commit()


def get_pump(session: Session) -> PumpState:
    config = session.exec(select(Config).where(Config.key == "pump")).one()
    return PumpState(config.value)


def set_pump(session: Session, pump: PumpState) -> None:
    config = session.exec(select(Config).where(Config.key == "pump")).one()
    config.value = pump.value
    session.add(config)
    session.commit()

def new_run(session: Session) -> int:
    last_run = session.exec(select(Run).order_by(Run.run_id.desc())).first()
    next_run_id = (last_run.run_id if last_run else 0) + 1
    new_run = Run(run_id=next_run_id, start_time=datetime.utcnow())
    session.add(new_run)
    session.commit()
    session.refresh(new_run)
    return new_run.run_id

def end_run(session: Session, run_id: int):
    run = session.exec(select(Run).where(Run.run_id == run_id)).first()
    if run:
        run.end_time = datetime.utcnow()
        session.add(run)
        session.commit()
