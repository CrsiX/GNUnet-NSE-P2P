import enum
import struct
import dataclasses
from typing import Iterable, Optional, Tuple


class MessageType(enum.IntEnum):
    """
    Enum listing all message types defined in the default API document

    Some of those message types are not used in the current NSE module
    implementation, but they are defined here for the sake of completeness.
    """

    GOSSIP_ANNOUNCE = 500
    GOSSIP_NOTIFY = 501
    GOSSIP_NOTIFICATION = 502
    GOSSIP_VALIDATION = 503

    NSE_QUERY = 520
    NSE_ESTIMATE = 521

    RPS_QUERY = 540
    RPS_PEER = 541

    ONION_TUNNEL_BUILD = 560
    ONION_TUNNEL_READY = 561
    ONION_TUNNEL_INCOMING = 562
    ONION_TUNNEL_DESTROY = 563
    ONION_TUNNEL_DATA = 564
    ONION_ERROR = 565
    ONION_COVER = 566

    AUTH_SESSION_START = 600
    AUTH_SESSION_HS1 = 601
    AUTH_SESSION_INCOMING_HS1 = 602
    AUTH_SESSION_HS2 = 603
    AUTH_SESSION_INCOMING_HS2 = 604
    AUTH_LAYER_ENCRYPT = 605
    AUTH_LAYER_DECRYPT = 606
    AUTH_LAYER_ENCRYPT_RESP = 607
    AUTH_LAYER_DECRYPT_RESP = 608
    AUTH_SESSION_CLOSE = 609
    AUTH_ERROR = 610
    AUTH_CIPHER_ENCRYPT = 611
    AUTH_CIPHER_ENCRYPT_RESP = 612
    AUTH_CIPHER_DECRYPT = 613
    AUTH_CIPHER_DECRYPT_RESP = 614

    DHT_PUT = 650
    DHT_GET = 651
    DHT_SUCCESS = 652
    DHT_FAILURE = 653

    ENROLL_INIT = 680
    ENROLL_REGISTER = 681
    ENROLL_SUCCESS = 682
    ENROLL_FAILURE = 683


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
