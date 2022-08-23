import math
import time
import socket
import asyncio
import logging
import ipaddress
from typing import Callable, ClassVar, Optional, Union

import sqlalchemy.orm

from . import config, persistence, utils
from .protocols import api, p2p


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
            api.unpack_incoming_message(data, [api.MessageType.NSE_QUERY])
            self.logger.info("Incoming API message: NSE_QUERY")
        except api.InvalidMessage as exc:
            self.logger.warning(f"Invalid API message: {exc}")
            self.logger.debug(f"First {min(len(data), 80)} bytes of incoming ignored/invalid message: {data[:80]}")
            return

        # Do message handling and write an answer using `self.transport.write(bytes)
        with persistence.get_new_session() as session:
            rounds = session.query(persistence.Round).order_by(persistence.Round.round.desc()) \
                .limit(config.NSEConfiguration.respected_rounds).all()
            rounds.pop(0)
            sum_of_peers = 0
            variance = 0
            n = len(rounds)
            for r in rounds:
                peers_in_r = int(get_size_estimate(r.proximity))
                sum_of_peers += peers_in_r
            peers = int(sum_of_peers / n)
            for r in rounds:
                variance += int(get_size_estimate(r.proximity) - peers)**2 / n
            std_deviation = int(variance ** 0.5)

            answer = api.pack_nse_estimate(peers, std_deviation)
            self.transport.write(answer)

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
        self._start_time = get_start_time(self._conf)
        self._own_proximity = p2p.calculate_proximity(self._conf.private_key, self._start_time)
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
            rounds = utils.get_rounds(session, self._current_round-1)
            if len(rounds) > 0:
                previous_estimate = get_size_estimate(rounds[0].proximity)
            # TODO: Optional improvement: store the past estimates in the database,
            #  then this lookup doesn't only depend on the very last round (use a new table!)

        delay = self.get_delay(self._conf.nse.frequency, self._own_proximity, previous_estimate)
        self.logger.debug(f"Starting... (round={self._current_round}, proximity={self._own_proximity}, delay={delay})")
        await asyncio.sleep(delay)

        # TODO: Lookup whether some better proximity for the current round appeared while waiting, then return

        msg = p2p.build_message(
            self._conf.private_key,
            self._start_time,
            logger=self.logger,
            proximity=self._own_proximity,
            proof_of_work_bits=self._conf.nse.proof_of_work_bits
        )
        success = self._write(msg)
        self.logger.debug(f"Announce {['failed', 'succeeded'][success]}! Message: {msg}")
        if not success:
            self.logger.warning("Failed to sent a gossip announcement!")

    @staticmethod
    def get_delay(frequency: int, proximity: int, previous_estimate: float) -> float:
        return frequency / 2 - (frequency / math.pi * math.atan(proximity - previous_estimate))


def get_size_estimate(expected_max_proximity: int) -> float:
    """
    Calculate a rough estimate of the current network size

    :param expected_max_proximity: expected number of max bits of proximity
    :return: estimated network size (it's a float, use with care)
    """

    return 2 ** (expected_max_proximity - 0.332747)


def get_current_round(freq: Union[int, config.Configuration], timestamp: Union[None, int, float] = None) -> int:
    """
    Calculate current round identifier based on a frequency (or config) and the timestamp

    :param freq: either a frequency (integer as seconds) or the configuration
    :param timestamp: optional timestamp to use (otherwise, use the current UNIX timestamp)
    :return: current round identifier
    """

    if isinstance(freq, config.Configuration):
        freq = freq.nse.frequency
    elif isinstance(freq, config.NSEConfiguration):
        freq = freq.frequency
    if timestamp is None:
        timestamp = time.time()
    timestamp = int(timestamp)
    return timestamp // freq


def get_start_time(freq: Union[int, config.Configuration], timestamp: Union[None, int, float] = None) -> int:
    """
    Calculate the current round's start time based on a frequency (or config) and the timestamp

    :param freq: either a frequency (integer as seconds) or the configuration
    :param timestamp: optional timestamp to use (otherwise, use the current UNIX timestamp)
    :return: exact UNIX timestamp when the current round has begun
    """

    if isinstance(freq, config.Configuration):
        freq = freq.nse.frequency
    elif isinstance(freq, config.NSEConfiguration):
        freq = freq.frequency
    if timestamp is None:
        timestamp = time.time()
    timestamp = int(timestamp)
    return timestamp - (timestamp % freq)


def get_remaining_time(freq: Union[int, config.Configuration], timestamp: Union[None, int, float] = None) -> int:
    """
    Calculate the remaining time in the current round based on a frequency (or config) and the timestamp

    :param freq: either a frequency (integer as seconds) or the configuration
    :param timestamp: optional timestamp to use (otherwise, use the current UNIX timestamp)
    :return: roughly remaining time of the current round in seconds
    """

    if isinstance(freq, config.Configuration):
        freq = freq.nse.frequency
    elif isinstance(freq, config.NSEConfiguration):
        freq = freq.frequency
    if timestamp is None:
        timestamp = time.time()
    timestamp = int(timestamp)
    return max(freq - timestamp % freq - 1, 0)
