"""
Module containing the main entrypoint to the program :func:`start`
as well as the :class:`Manager` which schedules and executes the
other parts of the whole project to fulfill their purposes
"""

import sys
import time
import asyncio
import logging
from typing import Optional

from . import config, gossip, nse, persistence, utils
from .protocols import api


class Manager:
    """
    Manager of program sub-tasks, executor of the NSE server, NSE scheduler and Gossip client

    :param conf: full package configuration instance
    """

    def __init__(self, conf: config.Configuration):
        self._conf = conf
        self._logger = logging.getLogger("manager")
        self._server: Optional[asyncio.AbstractServer] = None
        self._gossip_fails: int = 0
        self._gossip_protocol: Optional[asyncio.Protocol] = None
        self.gossip_transport: Optional[asyncio.Transport] = None

    async def _start_gossip_client(self, loop: asyncio.AbstractEventLoop, first: bool = False) -> bool:
        """
        Start a new instance of the Gossip API client class

        Note that this method adds itself to the event loop again if a later
        Gossip connection suddenly fails. It will wait exponentially longer
        the more re-connect attempts have previously failed.

        :param loop: running AsyncIO event loop which should execute the Gossip client
        :param first: switch to determine whether the current start is the first
            start of the Gossip client in the program's runtime
        :return: whether a new Gossip client has successfully established a connection
        :raises Exception: when the very first connection to the Gossip API fails
        """

        family, host, port = utils.split_ip_address_and_port(self._conf.gossip.api_address)
        try:
            self.gossip_transport, self._gossip_protocol = await loop.create_connection(
                lambda: gossip.Protocol(self._conf, self.reconnect_client), host, port, family=family
            )

        except Exception as exc:
            if first:
                if self.gossip_transport is None:
                    self._logger.critical(f"Failed to create a connection to gossip on {host} port {port}: {exc}")
                raise
            if self.gossip_transport and self.gossip_transport.is_closing():
                self.gossip_transport = None
            self._logger.warning(f"Failed to connect to gossip: {exc}")
            delay = 1.5 ** self._gossip_fails
            self._gossip_fails += 1
            self._logger.debug(f"Sleeping for {delay:.2f} seconds before the next auto-reconnect attempt ...")
            await asyncio.sleep(delay)
            loop.create_task(self._start_gossip_client(loop))
            return False

        if self._gossip_fails > 0:
            self._logger.info(f"Successfully established a gossip connection after {self._gossip_fails} attempts")
            self._gossip_fails = 0
        return True

    def reconnect_client(self):
        """
        Create an instant task in the event loop to (re)connect the Gossip client

        :return: None
        """

        loop = asyncio.get_event_loop()
        loop.create_task(self._start_gossip_client(loop))

    def _send_gossip_announce(self, data: bytes) -> bool:
        """
        Write arbitrary data as gossip announcement to the current network transport to the gossip API

        This function must be called in the context of an async function.

        :param data: arbitrary data in bytes
        :return: bool whether writing the data completed successfully
        """

        msg = api.pack_gossip_announce(self._conf.nse.data_type, data, self._conf.nse.data_gossip_ttl)
        if self.gossip_transport is None:
            self.reconnect_client()
            return False
        self.gossip_transport.write(msg)
        return True

    async def _schedule_nse_round(self):
        """
        Schedule the next NSE round and call continue recursively

        This recursive NSE round scheduler calls itself in regular intervals,
        depending on the setting of the NSE frequency. It will trigger one
        :meth:`p2p_nse5.nse.RoundHandler.run` call at the start of a new NSE round.

        :return: None
        """

        f = self._conf.nse.frequency
        await asyncio.sleep(f - int(time.time()) % f - 1)
        self._logger.debug(f"Triggering next NSE round participation (current time: {int(time.time())})")
        asyncio.get_running_loop().create_task(nse.RoundHandler(self._conf, self._send_gossip_announce).run())
        await asyncio.sleep(1)
        asyncio.get_running_loop().create_task(self._schedule_nse_round())

    async def run(self):
        """
        Main program routine

        This method contains a blocking call to
        :meth:`asyncio.events.AbstractServer.serve_forever`
        to keep the current event loop running.
        It's also the executor of the NSE API server,
        listening for incoming connections which uses
        :class:`p2p_nse5.nse.Protocol` as the protocol handler.
        It will start the recursive NSE scheduler
        :meth:`_schedule_nse_round` once at startup, after
        successfully having established a Gossip connection via
        :meth:`_start_gossip_client`.

        :return: does not return while the Manager executes,
            but will be quit via KeyboardInterrupt
        """

        event_loop = asyncio.get_running_loop()
        event_loop.create_task(self._schedule_nse_round())
        await self._start_gossip_client(event_loop, True)
        family, host, port = utils.split_ip_address_and_port(self._conf.nse.api_address)
        self._server = await event_loop.create_server(
            lambda: nse.Protocol(self._conf), host, port, family=family
        )
        self._logger.info("API server started on host %s and port %d", host, port)
        async with self._server:
            await self._server.serve_forever()


def start(conf: config.Configuration):
    """
    Setup logging & database and boot a :class:`Manager` to execute the main program

    :param conf: complete package configuration
    :return: does not return while the Manager executes,
        but will be quit via KeyboardInterrupt
    """

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
    logger.info("Starting...")

    logger.debug(f"Configuring database using {conf.nse.database!r} ...")
    persistence.init(conf.nse.database)

    try:
        asyncio.run(Manager(conf).run())
    except KeyboardInterrupt:
        logger.info("Exiting gracefully")
