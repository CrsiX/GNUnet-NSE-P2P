import asyncio
import logging
from typing import Optional

from . import config, utils


class APIProtocol(asyncio.Protocol):
    pass


class APIServer:
    def __init__(self, conf: config.Configuration):
        self._conf = conf
        self._logger = logging.getLogger("nse.server")
        self._server: Optional[asyncio.AbstractServer] = None

    async def run(self):
        event_loop = asyncio.get_running_loop()
        family, host, port = utils.split_ip_address_and_port(self._conf.nse.api_address)
        self._server = await event_loop.create_server(lambda: APIProtocol(), host, port, family=family)
        self._logger.info("API server started on host %s and port %d", host, port)
        async with self._server:
            await self._server.serve_forever()
