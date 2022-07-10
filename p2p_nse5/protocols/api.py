import dataclasses
import struct
from typing import Union

from .msg_types import MessageType


class InvalidMessage(Exception):
    """
    Exception for invalid API messages (they should simply be ignored)
    """


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


def pack_gossip_validation(message_id: int, valid: bool) -> bytes:
    pass  # TODO


def pack_nse_estimate(peers: int, std_deviation: int) -> bytes:
    pass  # TODO


def unpack_incoming_message(msg: bytes) -> (int, Union[bool, GossipNotification]):
    """
    Parse, validate and unpack an incoming API message into type and data

    :param msg: incoming unchecked message in raw bytes
    :return: tuple of the message type identifier and the
        unpacked value specific to the specific message type
    :raises InvalidMessage: when an unsupported message type was
        detected or when the message is malformed in any way
    """

    if len(msg) < 4 or len(msg) > 65535:
        raise InvalidMessage("Invalid length")
    try:
        size, msg_type = map(int, struct.Struct("!HH").unpack(msg[:4]))
        if size != len(msg):
            raise InvalidMessage("Invalid length field value")
    except (ValueError, struct.error) as exc:
        raise InvalidMessage("Invalid header start") from exc
    if msg_type == MessageType.NSE_QUERY:
        return msg_type, True
    elif msg_type == MessageType.GOSSIP_NOTIFICATION:
        if size < 8:
            raise InvalidMessage("Message too short")
        try:
            msg_id, data_type = map(int, struct.Struct("!HH").unpack(msg[4:8]))
        except (ValueError, struct.error) as exc:
            raise InvalidMessage("Invalid gossip notification message") from exc
        return msg_type, GossipNotification(size=size, message_id=msg_id, data_type=data_type, data=msg[8:])
    else:
        raise InvalidMessage(f"Unknown incoming message type: {msg_type}")
