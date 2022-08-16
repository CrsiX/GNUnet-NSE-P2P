"""
Database models and functions using SQLAlchemy
"""

import random
import string
import logging
import datetime
from typing import Optional

from sqlalchemy import create_engine, Column, DateTime, ForeignKey, func, Integer, LargeBinary
from sqlalchemy.engine import Engine as _Engine
from sqlalchemy.orm import declarative_base, relationship, sessionmaker, Session


DEFAULT_DATABASE_URL: str = f"sqlite:////tmp/nse_{''.join(random.choice(string.ascii_lowercase) for _ in '_' * 16)}.db"

Base = declarative_base()
_engine: Optional[_Engine] = None
_make_session: Optional[sessionmaker] = None


class Peer(Base):
    """
    Model of a peer in the network identified by the unique public key
    """

    __tablename__ = "peers"

    id: int = Column(Integer, nullable=False, primary_key=True, autoincrement=True, unique=True)
    public_key: bytes = Column(LargeBinary, nullable=False, unique=True)
    """RSA 4096 public key of the remote peer in DEM binary format"""
    interactions: int = Column(Integer, nullable=False, default=1)
    """Counter how often our NSE module contacted the peer's NSE module or vice versa"""
    created: datetime.datetime = Column(DateTime, nullable=False, server_default=func.now())
    updated: datetime.datetime = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    def __repr__(self) -> str:
        return f"Peer(id={self.id}, interactions={self.interactions})"


class Round(Base):
    """
    Model of a time round and related information like the best peer or the max hops
    """

    __tablename__ = "rounds"

    id: int = Column(Integer, nullable=False, primary_key=True, autoincrement=True, unique=True)
    round: int = Column(Integer, nullable=False, unique=True)
    """Round identifier"""
    proximity: int = Column(Integer, nullable=False)
    """Verified proximity measured in matching leading bits of the best peer (see `peer`)"""
    max_hops: int = Column(Integer, nullable=False, default=1)
    """Highest number of relaying hops in the round, not necessarily related to the best peer"""
    peer_id: int = Column(Integer, ForeignKey("peers.id"), nullable=False)
    """ID of the peer who sent the time sample to us"""
    peer: Peer = relationship("Peer", backref="rounds")
    """Relation to the peers, so that the `rounds` of a peer necessarily are the best rounds"""
    created: datetime.datetime = Column(DateTime, nullable=False, server_default=func.now())
    updated: datetime.datetime = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    def __repr__(self) -> str:
        return f"Round(id={self.id}, round={self.round}, proximity={self.proximity})"


def init(database_url: str, create_all: bool = True):
    """
    Initialize the database connections

    This function should be called at a very early program stage, before
    any part of it tries to access the database. If this isn't done,
    a temporary database will be used instead, which may be useful for
    debugging, too. See the ``DEFAULT_DATABASE_URL`` value for details
    about the default connection. Without initialization prior to database
    usage, a warning will be emitted once to prevent future errors.

    :param database_url: the full URL to connect to the database
    :param create_all: whether the metadata of the declarative base should
        be used to create all non-existing tables in the database
    """

    global _engine, _make_session
    if database_url == DEFAULT_DATABASE_URL:
        logging.getLogger("persistence").warning(
            f"Using the default database URL {database_url!r} may provide no persistent "
            f"and reliable data storage, please adjust the program settings."
        )

    if database_url.startswith("sqlite:"):
        _engine = create_engine(database_url, echo=False, connect_args={"check_same_thread": False})
    else:
        _engine = create_engine(database_url, echo=False)

    if create_all:
        Base.metadata.create_all(bind=_engine)

    _make_session = sessionmaker(autocommit=False, autoflush=False, bind=_engine)


def _warn(obj: str):
    logging.getLogger("persistence").warning(
        f"Database {obj} not initialized! Using default database URL with database "
        f"{DEFAULT_DATABASE_URL!r}. Call 'init' once at program startup to fix "
        f"future problems due to non-persistent database and suppress this warning."
    )


def get_engine() -> _Engine:
    if _engine is None:
        _warn("engine")
        init(DEFAULT_DATABASE_URL)
    return _engine


def get_new_session() -> Session:
    if _make_session is None or _engine is None:
        _warn("engine or its session maker")
        init(DEFAULT_DATABASE_URL)
    return _make_session()
