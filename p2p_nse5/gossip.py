import time
import asyncio
import hashlib
import logging
from typing import Callable, ClassVar, Optional

from . import config, persistence, utils
from .protocols import api, msg_types, p2p


class Protocol(asyncio.Protocol):
    """
    Implementation of the API protocol to/from the gossip module dependency using the asyncio framework
    """

    _instance_counter: ClassVar = utils.counter()

    def __init__(self, conf: config.Configuration, reconnect: Optional[Callable[[], None]] = None):
        self._conf: config.Configuration = conf
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
        data = api.pack_gossip_notify(self._conf.nse.data_type)
        self.logger.debug(f"Sending packet to gossip endpoint: {data} (data type: {self._conf.nse.data_type})")
        transport.write(data)

    def data_received(self, data: bytes) -> None:
        try:
            msg_type, value = api.unpack_incoming_message(data, [msg_types.MessageType.GOSSIP_NOTIFICATION])
            self.logger.debug(f"Incoming API message: {msg_type=!r}")
        except api.InvalidMessage as exc:
            self.logger.warning(f"Invalid API message: {exc}")
            self.logger.debug(f"First {min(len(data), 80)} bytes of incoming ignored/invalid message: {data[:80]}")
            return

        try:
            notification = p2p.unpack_message(
                value.data,
                min_proximity=0,
                proof_of_work_bits=self._conf.nse.proof_of_work_bits
            )
            r = notification.round_time // self._conf.nse.frequency
            self.logger.debug(f"Successfully parsed gossip notification: {notification!r} (round {r})")
            der_key = notification.public_key.export_key("DER")
        except ValueError as exc:
            self.logger.warning(f"Invalid GOSSIP_NOTIFICATION: {exc}")
            self.transport.write(api.pack_gossip_validation(value.message_id, False))
            return

        # Determining the peer and adding them to our dataset for more efficient storage of rounds
        current_round = int(time.time()) // self._conf.nse.frequency
        with persistence.get_new_session() as session:
            peers = session.query(persistence.Peer).filter_by(public_key=der_key).all()
            if len(peers) == 1:
                peer = peers[0]
                self.logger.debug(f"Found peer {peer.id!r} ({peer.interactions!r}) with matching public key")
            elif len(peers) == 0:
                peer = persistence.Peer(public_key=der_key, interactions=1)
                session.add(peer)
                session.commit()
                h = hashlib.sha256(notification.public_key.export_key("PEM")).hexdigest()
                self.logger.debug(f"New peer {peer.id} created for new public key (hash: {h})")

            # Notifications for the current round are accepted when they have a sufficiently high proximity
            if r == current_round:
                rounds = utils.get_rounds(session, current_round)
                if len(rounds) > 0:
                    best_round = rounds[0]
                    # TODO: Should we also answer with an immediate update indicating a higher
                    #  proximity to the specified peer? This is only possible if our NSE module
                    #  had its own P2P connectivity to other peers in the network.
                    if best_round.proximity >= notification.proximity:
                        self.logger.debug(f"Too low proximity {notification.proximity} (best: {best_round.proximity})")
                        self.transport.write(api.pack_gossip_validation(value.message_id, False))
                        return
                session.add(persistence.Round(
                    round=current_round,
                    backlog=False,
                    proximity=notification.proximity,
                    max_hops=notification.hop_count,
                    peer=peer
                ))
                session.commit()
                self.transport.write(api.pack_gossip_validation(value.message_id, True))

            # Notifications with a round in the future are added as 'backlog' and won't be handled now
            elif r > current_round and r - current_round <= self._conf.nse.max_backlog_rounds:
                self.logger.debug(f"Notification comes from a future round (r={r}, current={current_round}")
                session.add(persistence.Round(
                    round=r,
                    backlog=True,
                    proximity=notification.proximity,
                    max_hops=notification.hop_count,
                    peer=peer
                ))
                session.commit()
                self.transport.write(api.pack_gossip_validation(value.message_id, True))
                return

            # Notifications from the past or too far ahead in the future are ignored
            else:
                self.logger.debug(f"Notification (r={r}) is outdated or too far ahead for now ({current_round})")
                self.transport.write(api.pack_gossip_validation(value.message_id, False))
                return

    def eof_received(self) -> Optional[bool]:
        self.logger.error("Received EOF from gossip. Trying to re-connect ...")
        self.transport.close()
        if self._reconnect is not None:
            asyncio.get_event_loop().call_soon(self._reconnect)
        return False

    def connection_lost(self, exc: Optional[Exception]) -> None:
        self.logger.error("Lost connection to gossip. Trying to re-connect ...", exc_info=exc)
        self.transport.close()
        if self._reconnect is not None:
            asyncio.get_event_loop().call_soon(self._reconnect)
