import dataclasses
from typing import Any


@dataclasses.dataclass
class GossipNotification:
    size: int
    message_id: int
    data_type: int
    data: bytes


def pack_gossip_announce(data_type: int, data: bytes, ttl: int) -> bytes:
    pass


def pack_gossip_notify(data_type: int) -> bytes:
    pass  # TODO


def unpack_gossip_notification(msg: bytes) -> GossipNotification:
    pass  # TODO


def pack_gossip_validation(message_id: int, valid: bool) -> bytes:
    pass  # TODO


def unpack_nse_query(msg: bytes) -> bool:
    pass  # TODO


def pack_nse_estimate(peers: int, std_deviation: int) -> bytes:
    pass  # TODO


def unpack_incoming_message(msg: bytes) -> (int, Any):
    """
    Parse, validate and unpack an incoming API message into type and data

    :param msg: incoming unchecked message in raw bytes
    :return: tuple of the message type identifier and the
        unpacked value specific to the specific message type
    :raises ValueError: when an unsupported message type was
        detected or when the message is malformed in any way
    """

    pass  # TODO
