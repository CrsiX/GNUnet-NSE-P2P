"""
Module handling interactions with other NSE API clients and other NSE peers via Gossip
"""

import math
import time
import random
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

    :param configuration: package configuration instance for a NSE5 instance
    """

    _instance_counter: ClassVar = utils.counter()
    """Simple counter to give every instance of this class a new increasing number"""

    def __init__(self, configuration: config.Configuration):
        self._ident: int = next(type(self)._instance_counter)
        self.logger: logging.Logger = logging.getLogger(f"nse.handler.{self._ident}")
        self.config: config.Configuration = configuration
        self.transport: Optional[asyncio.Transport] = None
        self.family: socket.AddressFamily
        self.family, _, _ = utils.split_ip_address_and_port(self.config.nse.api_address)
        self.session: Optional[sqlalchemy.orm.Session] = None

    def connection_made(self, transport: asyncio.Transport) -> None:
        """
        Handler to be called when a connection is made

        The transport must be an IPv4 or IPv6 transport, depending on
        which kind of API listen address has been configured in
        :class:`p2p_nse5.config.NSEConfiguration`. If
        :attr:`p2p_nse5.config.NSEConfiguration.enforce_localhost` is set
        and the remote end is no local interface, the connection
        will be closed.

        :param transport: transport representing the pipe connection
        :return: None
        """

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
        """
        Handler to be called when some data is received by the underlying TCP transport

        This method will first attempt to parse the incoming TCP packet as
        a ``NSE_QUERY`` API message, since no other messages are
        expected on the protocol's TCP connection anyways. If this
        fails, the message is silently discarded.

        Then, the database is queried for the most recent rounds
        known to the peer, to calculate the overall network size
        estimate and standard deviation. Those values are then
        returned via the same transport as ``NSE_ESTIMATE`` message.

        :param data: incoming raw message (buffer of bytes from the underlying TCP connection)
        :return: None
        """

        try:
            api.unpack_incoming_message(data, [api.MessageType.NSE_QUERY])
            self.logger.info("Incoming API message: NSE_QUERY")
        except api.InvalidMessage as exc:
            self.logger.warning(f"Invalid API message: {exc}")
            self.logger.debug(f"First {min(len(data), 80)} bytes of incoming ignored/invalid message: {data[:80]}")
            return

        # Handle the incoming message and respond with an NSE_ESTIMATE answer
        with persistence.get_new_session() as session:
            rounds = session.query(persistence.Round) \
                .filter(persistence.Round.round <= get_current_round(self.config.nse.frequency)) \
                .limit(self.config.nse.respected_rounds).all()

            proximity_values = list(map(lambda p: p.proximity, rounds))
            std_deviation = utils.get_std_deviation(proximity_values)
            total_peers = round(sum(map(get_size_estimate, proximity_values)))
            answer = api.pack_nse_estimate(total_peers, std_deviation)
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

    :param conf: package configuration instance for a NSE5 instance
    :param write: callable accepting some bytes which should be written
        to the currently active transport to the Gossip API server,
        so that NSE information can be successfully spread in the network
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
            rounds = session.query(persistence.Round).filter_by(round=self._current_round - 1).all()
            if len(rounds) > 0:
                previous_estimate = get_size_estimate(rounds[0].proximity)

        delay = get_delay(self._conf.nse.frequency, self._own_proximity, previous_estimate)
        self.logger.debug(f"Starting... (round={self._current_round}, proximity={self._own_proximity}, delay={delay})")
        await asyncio.sleep(delay * (1 + random.random() / 20))

        # Return when some equal or better proximity for the current round appeared while waiting
        with persistence.get_new_session() as session:
            rounds = session.query(persistence.Round).filter_by(round=self._current_round).all()
            if len(rounds) > 0:
                if rounds[0].proximity >= self._own_proximity:
                    self.logger.debug(
                        f"Cancelling the broadcast of the current round's estimate, found proximity "
                        f"{rounds[0].proximity} from peer ID {rounds[0].peer_id}"
                    )
                    return

        # Build our own P2P message and hand it over to gossip to spread in the network
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


def get_delay(frequency: int, proximity: int, previous_estimate: float) -> float:
    """
    Calculate the initial delay for starting the flood using the formula by Evans et. al.

    :param frequency: configured network-wide frequency for new size estimate floods
    :param proximity: calculated own proximity in the current round
    :param previous_estimate: network size estimate calculated at the end of the previous round
    :return:
    """

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
