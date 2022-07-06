import dataclasses


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
