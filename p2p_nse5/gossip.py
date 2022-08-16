import asyncio
import logging
from typing import Optional

from . import nse
from .protocols import api


class Client(asyncio.Protocol):
    def __init__(self, api_data_type: int, srv: nse.Server):
        self._data_type: int = api_data_type
        self._logger = logging.getLogger("gossip.client")
        self._server: nse.Server = srv
        self.transport: Optional[asyncio.Transport] = None

    def connection_made(self, transport: asyncio.Transport) -> None:
        self.transport = transport
        self._logger.info(
            "Successfully established gossip connection to %s port %d",
            *transport.get_extra_info("peername")[:2]
        )
        data = api.pack_gossip_notify(self._data_type)
        self._logger.debug("Sending packet to gossip endpoint: %s (data type: %d)", data, self._data_type)
        transport.write(data)

    def data_received(self, data: bytes) -> None:
        self._logger.warning(f"Received {len(data)} unexpected bytes from gossip API connection, ignoring")
        self._logger.debug(f"First {min(len(data), 80)} bytes of incoming ignored data: %d", data[:80])

    def eof_received(self) -> Optional[bool]:
        self._logger.error("Received EOF from gossip. Trying to re-connect ...")
        self.transport.close()
        return False

    def connection_lost(self, exc: Optional[Exception]) -> None:
        self._logger.error("Lost connection to gossip. Trying to re-connect ...", exc_info=exc)
        self.transport.close()
        asyncio.get_event_loop().call_soon(self._server.reconnect_client())
