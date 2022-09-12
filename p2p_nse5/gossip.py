"""
Module handling interactions with the Gossip API server
"""

import time
import asyncio
import hashlib
import logging
from typing import Callable, ClassVar, Optional

from . import config, persistence, utils
from .protocols import api, p2p


class Protocol(asyncio.Protocol):
    """
    Implementation of the API protocol to/from the gossip module dependency using the asyncio framework

    :param conf: package configuration instance for a NSE5 instance
    :param reconnect: callable that should trigger a reconnection attempt
        of the connection to the Gossip API server, which is usually supplied by
        a manager class, e.g. :class:`p2p_nse5.entrypoint.Manager`
    """

    _instance_counter: ClassVar = utils.counter()
    """Simple counter to give every instance of this class a new increasing number"""

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
        """
        Handler to be called when some data is received by the underlying TCP transport

        This method will first attempt to parse the incoming TCP packet as
        a ``GOSSIP_NOTIFICATION`` API message, since no other messages are
        expected on the Gossip TCP connection anyways. If this fails, the
        message is silently discarded. Then, the payload of that message will be
        unpacked as instance of our P2P protocol. If this fails, the message is
        discarded, and the Gossip server will be notified of an invalid message.
        In this step, the proof of work is also forcefully verified by
        :func:`p2p_nse5.protocols.p2p.unpack_message`.

        The remote peer's public key will now be extracted from the validated
        gossip message. If the peer is already known in the database, the
        peer ID can be looked up; otherwise, a new peer entry will be created.

        Next, the round is identified. If it's too far in the past or future,
        the message will be invalidated. Otherwise, if the proximity of the
        message is sufficiently large (at least one bit higher than any previous
        proximity for the specified round), it will be accepted.

        :param data: incoming raw message (buffer of bytes from the underlying TCP connection)
        :return: None
        """

        try:
            msg_type, value = api.unpack_incoming_message(data, [api.MessageType.GOSSIP_NOTIFICATION])
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

        current_round = int(time.time()) // self._conf.nse.frequency
        with persistence.get_new_session() as session:

            # Determining the peer and adding them to our dataset for more efficient storage of rounds
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

            # Notifications for the current round or any round in the future
            # (as long as it's not too far ahead) are accepted when they have a
            # sufficiently high proximity or as the first notification for that round
            if r == current_round or (r > current_round and r - current_round <= self._conf.nse.max_backlog_rounds):
                if r > current_round:
                    self.logger.debug(f"Notification comes from a future round (r={r}, current={current_round})")

                model = session.query(persistence.Round).filter_by(round=current_round).first()
                if model is not None:
                    # TODO: Should we also answer with an immediate update indicating a higher
                    #  proximity to the specified peer? This is only possible if our NSE module
                    #  had its own P2P connectivity to other peers in the network.
                    if model.proximity >= notification.proximity:
                        self.logger.debug(f"Too low proximity {notification.proximity} (best: {model.proximity})")
                        self.transport.write(api.pack_gossip_validation(value.message_id, False))
                        return

                    model.proximity = notification.proximity
                    model.max_hops = max(notification.hop_count, model.max_hops)
                    model.peer = peer
                    session.add(model)
                    session.commit()
                    self.logger.info(f"Updated round {model.round} to proximity {model.proximity} (peer ID: {peer.id})")
                    self.transport.write(api.pack_gossip_validation(value.message_id, True))
                    return

                m = persistence.Round(
                    round=current_round,
                    proximity=notification.proximity,
                    max_hops=notification.hop_count,
                    peer=peer
                )
                session.add(m)
                session.commit()
                self.logger.info(
                    f"Added new round entry {m.id} for {current_round} with proximity "
                    f"{m.proximity} and max_hops {m.max_hops} (peer ID: {peer.id})"
                )
                self.transport.write(api.pack_gossip_validation(value.message_id, True))

            # Notifications from the past or too far ahead in the future are ignored
            else:
                self.logger.debug(f"Notification (r={r}) is outdated or too far ahead for now ({current_round})")
                self.transport.write(api.pack_gossip_validation(value.message_id, False))

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
