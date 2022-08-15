import socket
import struct
import asyncio
import logging
import ipaddress
from typing import Dict, Callable, ClassVar, Optional

import sqlalchemy.orm

from .protocols.msg_types import MessageType
# from .protocols import api  # TODO: Use the methods provided by that module
from . import config, utils
from .protocols import api


class MessageHandler:
    def handle_message(self, message):
        try:
            #TODO Probably replace that with unpack_incoming_messages method
            data = struct.unpack('!2H', b"")  # data)
            msgtype = data[1]

            #TODO replace None by writer
            if (data[1] == MessageType.NSE_QUERY):
                self.handle_query(data, None)
            elif (data[1] == MessageType.GOSSIP_NOTIFICATION):
                self.handle_notification(self, data, None)
            else:
                print("Unreognized MessageType")

        except Exception:
            print("Something went wrong")

    # Handles a query request call
    async def handle_query(self, data, writer):
        # TODO Replace first 0 by "get_peer_estimation" and second 0 by "get_std_deviation"
        # Write the estimate
        estimate = self.assemble_answer(self, 0, 0)
        writer.write(estimate)
        await writer.drain()
        writer.close()

    async def handle_notification(self, data, writer):
        pass


    def assemble_answer(self, peers, std_deviation):
        return struct.pack('!2H2I', 16, MessageType.NSE_ESTIMATE, int(peers), int(std_deviation))




class APIProtocol(asyncio.Protocol):
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

        if not ip.is_loopback:
            self.logger.warning("Blocked incoming connection from %s port %d (not localhost!)", host, port)
            self.transport.write_eof()
            self.transport.close()
            return
        self.logger.info("Accepted incoming connection from %s port %d", host, port)

    def data_received(self, data: bytes) -> None:
        try:
            msg_type, value = api.unpack_incoming_message(data)
            self.logger.info(f"Incoming API message: {msg_type=!r} {value=!r}")
        except api.InvalidMessage as exc:
            self.logger.warning(f"Invalid API message: {exc}")
            if len(data) < 80:
                self.logger.debug("Full data: %s", data)
            else:
                self.logger.debug(f"Full data is {len(data)} bytes long. Skipped as too big API message.")

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
