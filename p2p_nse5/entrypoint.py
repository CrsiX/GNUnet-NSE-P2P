import sys
import asyncio
import logging
from typing import Optional

from . import config, gossip, nse, persistence, utils


class Manager:
    def __init__(self, conf: config.Configuration):
        self._conf = conf
        self._logger = logging.getLogger("manager")
        self._server: Optional[asyncio.AbstractServer] = None
        self._gossip_fails: int = 0
        self._gossip_protocol: Optional[asyncio.Protocol] = None
        self.gossip_transport: Optional[asyncio.Transport] = None

    async def _start_gossip_client(self, loop: asyncio.AbstractEventLoop, first: bool = False) -> bool:
        family, host, port = utils.split_ip_address_and_port(self._conf.gossip.api_address)
        try:
            self.gossip_transport, self._gossip_protocol = await loop.create_connection(
                lambda: gossip.Protocol(self._conf.nse.data_type, self.reconnect_client), host, port, family=family
            )

        except Exception as exc:
            if first:
                if self.gossip_transport is None:
                    self._logger.critical("Failed to create a connection to gossip on %s port %d: %s", host, port, exc)
                raise
            self._logger.warning("Failed to connect to gossip: %s", exc)
            delay = 1.5 ** self._gossip_fails
            self._gossip_fails += 1
            self._logger.debug("Sleeping for %.2f seconds before the next re-connect attempt ...", delay)
            await asyncio.sleep(delay)
            loop.create_task(self._start_gossip_client(loop))
            return False

        if self._gossip_fails > 0:
            self._logger.info("Successfully established a gossip connection after %d attempts", self._gossip_fails)
            self._gossip_fails = 0
        return True

    def reconnect_client(self):
        loop = asyncio.get_event_loop()
        loop.create_task(self._start_gossip_client(loop))

    async def run(self):
        event_loop = asyncio.get_running_loop()
        await self._start_gossip_client(event_loop, True)
        family, host, port = utils.split_ip_address_and_port(self._conf.nse.api_address)
        self._server = await event_loop.create_server(
            lambda: nse.Protocol(self._conf), host, port, family=family
        )
        self._logger.info("API server started on host %s and port %d", host, port)
        async with self._server:
            await self._server.serve_forever()


def start(conf: config.Configuration):
    log_conf = {
        "datefmt": conf.nse.log_dateformat,
        "format": conf.nse.log_format,
        "level": conf.nse.log_level,
        "style": conf.nse.log_style
    }

    if conf.nse.log_file not in ["", "-", "stdout", "stderr"]:
        log_conf["filename"] = conf.nse.log_file
    elif conf.nse.log_file == "stderr":
        log_conf["stream"] = sys.stderr
    elif conf.nse.log_file == "stdout":
        log_conf["stream"] = sys.stdout
    logging.basicConfig(**log_conf)

    logger = logging.getLogger("entrypoint")
    logger.debug("Starting...")

    persistence.init(conf.nse.database)

    try:
        asyncio.run(Manager(conf).run())
    except KeyboardInterrupt:
        logger.info("Exiting gracefully")
