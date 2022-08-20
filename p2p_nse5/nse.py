import math
import time
import socket
import asyncio
import logging
import ipaddress
from typing import Callable, ClassVar, Optional

import sqlalchemy.orm

from . import config, persistence, utils
from .protocols import api, msg_types, p2p


class Protocol(asyncio.Protocol):
    """
    Implementation of the API protocol for the NSE module using the asyncio framework
    """

    _instance_counter: ClassVar = utils.counter()

    def __init__(self, configuration: config.Configuration):
        self._ident: int = next(type(self)._instance_counter)
        self.logger: logging.Logger = logging.getLogger(f"nse.handler.{self._ident}")
        self.config: config.Configuration = configuration
        self.transport: Optional[asyncio.Transport] = None
        self.family: socket.AddressFamily
        self.family, _, _ = utils.split_ip_address_and_port(self.config.nse.api_address)
        self.session: Optional[sqlalchemy.orm.Session] = None

    def connection_made(self, transport: asyncio.Transport) -> None:
        self.transport = transport
        if self.family == socket.AF_INET:
            host, port = transport.get_extra_info("peername", [None, None])
            ip = ipaddress.IPv4Address(host)
        elif self.family == socket.AF_INET6:
            host, port, _, _ = transport.get_extra_info("peername", [None, None, None, None])
            ip = ipaddress.IPv6Address(host)
        else:
            raise RuntimeError("Unsupported address family")

        if not ip.is_loopback and self.config.nse.enforce_localhost:
            self.logger.warning("Blocked incoming connection from %s port %d (not localhost!)", host, port)
            self.transport.write_eof()
            self.transport.close()
            return
        self.logger.info("Accepted incoming connection from %s port %d", host, port)

    def data_received(self, data: bytes) -> None:
        try:
            api.unpack_incoming_message(data, [msg_types.MessageType.NSE_QUERY])
            self.logger.info(f"Incoming API message: NSE_QUERY")
        except api.InvalidMessage as exc:
            self.logger.warning(f"Invalid API message: {exc}")
            self.logger.debug(f"First {min(len(data), 80)} bytes of incoming ignored/invalid message: {data[:80]}")
            return

        # TODO: Do message handling and write an answer using `self.transport.write(bytes)`

        if self.transport.can_write_eof():
            self.transport.write_eof()
        self.transport.close()

    def eof_received(self) -> Optional[bool]:
        self.logger.debug("Received EOF on transport (closing connection)")
        if not self.transport.is_closing():
            self.transport.close()
        return False

    def connection_lost(self, exc: Optional[Exception]) -> None:
        if exc is None:
            self.logger.debug("Lost connection to remote end")
        else:
            self.logger.debug("Lost connection to remote side (reason: %s)", str(exc), exc_info=exc)
        if not self.transport.is_closing():
            self.transport.close()


class RoundHandler:
    """
    Handler class for a single iteration (round) of the GNUnet NSE algorithm
    """

    def __init__(self, conf: config.Configuration, write: Callable[[bytes], bool]):
        self._conf = conf
        self._write = write
        self._current_round = int(time.time()) // self._conf.nse.frequency
        self._own_proximity = p2p.calculate_proximity(self._conf.private_key, self._current_round)
        self.logger: logging.Logger = logging.getLogger(f"nse.round.{self._current_round}")

    async def run(self) -> None:
        """
        Execute the NSE round handler algorithm based on GNUnet NSE

        Rough description of this function:
          1. Get the previous network size estimate
          2. Wait a delay based on our proximity (lower proximity waits longer)
          3. Lookup whether some better proximity for the current round appeared while waiting
          4. If we're worse than the current proximity, return
          5. Otherwise announce our own proximity in a valid P2P message to the gossip API

        :return: None
        """

        # Get the previous estimate either from the database or use 1 for the first round
        previous_estimate = 1.0
        with persistence.get_new_session() as session:
            rounds = list(sorted(
                session.query(persistence.Round).filter_by(round=self._current_round-1).all(),
                key=lambda o: int(o.proximity),
                reverse=True
            ))
            if len(rounds) > 0:
                previous_estimate = calc_size_estimate(rounds[0].proximity)
            # TODO: Optional improvement: store the past estimates in the database,
            #  then this lookup doesn't only depend on the very last round (use a new table!)

        delay = self.get_delay(self._conf.nse.frequency, self._own_proximity, previous_estimate)
        self.logger.debug(f"Starting... (round={self._current_round}, proximity={self._own_proximity}, delay={delay})")
        await asyncio.sleep(delay)

        # TODO: Lookup whether some better proximity for the current round appeared while waiting, then return

        msg = p2p.build_message(self._conf.private_key, self._current_round, self.logger, self._own_proximity)
        success = self._write(msg)
        self.logger.debug(f"Announce {['failed', 'succeeded'][success]}! Message: {msg}")
        if not success:
            self.logger.warning("Failed to sent a gossip announcement successfully!")

    @staticmethod
    def get_delay(frequency: int, proximity: int, previous_estimate: float) -> float:
        return frequency / 2 - (frequency / math.pi * math.atan(proximity - previous_estimate))


def calc_size_estimate(expected_max_proximity: int) -> float:
    """
    Calculate a rough estimate of the current network size

    :param expected_max_proximity: expected number of max bits of proximity
    :return: estimated network size (it's a float, use with care)
    """

    return 2 ** (expected_max_proximity - 0.332747)
