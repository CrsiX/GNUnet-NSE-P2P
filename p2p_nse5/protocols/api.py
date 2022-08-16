import struct
import dataclasses
from typing import Iterable, Optional, Tuple

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
    header = struct.Struct("!HHBxH").pack(8 + len(data), MessageType.GOSSIP_ANNOUNCE, ttl, data_type)
    return header + data


def pack_gossip_notify(data_type: int) -> bytes:
    return struct.Struct("!HHHH").pack(8, MessageType.GOSSIP_NOTIFY, 0, data_type)


def pack_gossip_validation(message_id: int, valid: bool) -> bytes:
    return struct.Struct("!HHHH").pack(8, MessageType.GOSSIP_VALIDATION, message_id, int(valid))


def pack_nse_estimate(peers: int, std_deviation: int) -> bytes:
    return struct.Struct("!HHII").pack(12, MessageType.NSE_ESTIMATE, peers, std_deviation)


def unpack_incoming_message(
        msg: bytes,
        expected_types: Optional[Iterable[int]] = None
) -> Tuple[int, Optional[GossipNotification]]:
    """
    Parse, validate and unpack an incoming API message into type and data

    :param msg: incoming unchecked message in raw bytes
    :param expected_types: iterable of expected message types
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
    try:
        msg_type_name = MessageType(msg_type)
    except ValueError as exc:
        raise InvalidMessage(f"Unknown API message type '{msg_type}'") from exc
    if expected_types and msg_type not in expected_types:
        raise InvalidMessage(f"Unexpected message type {msg_type_name!s}")
    if msg_type == MessageType.NSE_QUERY:
        return msg_type, None
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
