from sqlmodel import Session, SQLModel, create_engine, select

from models import Config, Mode

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
            session.add(Config(key="mode", value=Mode.AUTO.value))
            session.commit()


def get_session() -> Session:
    """Yield a SQLModel session for use as a FastAPI dependency."""
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
