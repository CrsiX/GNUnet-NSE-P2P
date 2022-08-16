import asyncio
import logging
from typing import Callable, ClassVar, Optional

from . import utils
from .protocols import api, msg_types, p2p


class Protocol(asyncio.Protocol):
    _instance_counter: ClassVar = utils.counter()

    def __init__(self, data_type: int, reconnect: Optional[Callable[[], None]] = None):
        self._data_type: int = data_type
        self._ident: int = next(type(self)._instance_counter)
        self._reconnect: Optional[Callable[[], None]] = reconnect
        self.logger: logging.Logger = logging.getLogger(f"gossip.client.{self._ident}")
        self.transport: Optional[asyncio.Transport] = None

    def connection_made(self, transport: asyncio.Transport) -> None:
        self.transport = transport
        self.logger.info(
            "Successfully established gossip connection to %s port %d",
            *transport.get_extra_info("peername")[:2]
        )
        data = api.pack_gossip_notify(self._data_type)
        self.logger.debug(f"Sending packet to gossip endpoint: {data} (data type: {self._data_type})")
        transport.write(data)

    def data_received(self, data: bytes) -> None:
        try:
            msg_type, value = api.unpack_incoming_message(data, [msg_types.MessageType.GOSSIP_NOTIFICATION])
            self.logger.info(f"Incoming API message: {msg_type=!r} {value=!r}")
        except api.InvalidMessage as exc:
            self.logger.warning(f"Invalid API message: {exc}")
            self.logger.debug(f"First {min(len(data), 80)} bytes of incoming ignored/invalid message: {data[:80]}")
            return

        try:
            notification = p2p.unpack_message(value.data)
            self.transport.write(api.pack_gossip_validation(value.message_id, True))
        except ValueError as exc:
            self.logger.warning(f"Invalid GOSSIP_NOTIFICATION: {exc}")
            self.transport.write(api.pack_gossip_validation(value.message_id, False))
            return

        # TODO: Handle ProtocolMessage `notification`

    def eof_received(self) -> Optional[bool]:
        self.logger.error("Received EOF from gossip. Trying to re-connect ...")
        self.transport.close()
        return False

    def connection_lost(self, exc: Optional[Exception]) -> None:
        self.logger.error("Lost connection to gossip. Trying to re-connect ...", exc_info=exc)
        self.transport.close()
        if self._reconnect is not None:
            asyncio.get_event_loop().call_soon(self._reconnect)
