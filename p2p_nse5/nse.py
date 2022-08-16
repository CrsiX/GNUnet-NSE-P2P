import socket
import asyncio
import logging
import ipaddress
from typing import ClassVar, Optional

import sqlalchemy.orm

from . import config, utils
from .protocols import api, msg_types


class Protocol(asyncio.Protocol):
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
