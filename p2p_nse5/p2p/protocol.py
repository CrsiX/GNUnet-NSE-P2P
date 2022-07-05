import math
import time
import struct
import hashlib
import logging
import dataclasses
from typing import Union

from Crypto.PublicKey import RSA
from Crypto.Signature import pss
from Crypto.Hash import SHA512


# Protocol structure:
# 1 byte    | header code (static `0x42`)
# 1 byte    | hop count (updated at each relaying peer)
# 2 bytes   | length of the RSA public key in bytes (see below)
# 4 bytes   | proximity in bits
# 8 bytes   | time of the round
# 8 bytes   | random sample data for the proof of work
# var bytes | RSA public key in DEM binary format
# 512 bytes | 4096-bit RSA signature of everything except the first 2 bytes
PROTOCOL_HEADER = struct.Struct("!cBHLQQ")
HASHED_HEADER = struct.Struct("!HLQQ")
HEADER_CODE = b"*"
HEADER_LENGTH = 24
SIGNATURE_LENGTH = 512

DEFAULT_HOP_COUNT = 64
DEFAULT_PROOF_OF_WORK_BITS = 20  # TODO: Check which number of PoW bits is sufficient for the network
HASH_ENDIAN = "big"


@dataclasses.dataclass
class ProtocolMessage:
    """
    Simple dataclass carrying the values of a valid incoming NSE protocol message
    """

    round_time: int
    proximity: int
    public_key: RSA.RsaKey


def _check_proof_of_work(required_bits: int, body: bytes) -> bool:
    h = hashlib.sha256(body).digest()
    return int.from_bytes(h[-math.ceil(required_bits / 8):], HASH_ENDIAN) % (1 << required_bits) == 0


def calculate_proximity(rsa_key: RSA.RsaKey, value: Union[int, bytes]) -> int:
    """
    Determine the proximity as number of equal leading bits between the
    RSA public key's N and some comparison value's unsalted SHA256 hash

    :param rsa_key: RSA public key of at least 1024 bits size
    :param value: some comparison value, usually a representation of the round time
    :return: number of equal leading bits between the hashed value and the public key
    """

    # Convert possibly large integer values to big endian bytearrays
    if isinstance(value, int):
        ba = bytearray()
        while value > 255:
            ba.append(value % 256)
            value = value >> 8
        ba.append(value)
        value = bytes(ba)
    elif not isinstance(value, bytes):
        raise TypeError(f"Expected bytes or int, not {type(value)}")
    h_ = int.from_bytes(hashlib.sha256(value).digest(), HASH_ENDIAN)

    # Using binary representations and string operations is hacky but easy
    n = bin(rsa_key.public_key().n)[2:]
    h = bin(h_)[2:]
    while len(h) < 256:
        h = "0" + h
    c = 0
    proximity = 0
    while c < 256 and h[c] == n[c]:
        proximity += 1
        c += 1
    return proximity


def build_message(
        rsa_key: RSA.RsaKey,
        round_time: int,
        logger: logging.Logger = None,
        proximity: int = None,
        proof_of_work_bits: int = None,
        hop_count: int = None
) -> bytes:
    """
    Construct a binary NSE protocol message from a set of input values

    :param rsa_key: private and public key pair of a 4096 bit RSA key
    :param round_time: round time which is spread across the network
    :param logger: optional logger to keep track of the PoW calculation time
    :param proximity: optional number of equal leading bits between the
        hash of the round time (target identity) and the key identity;
        it will be generated on demand of not explicitly given
    :param proof_of_work_bits: optional override of the required
        trailing zero bits of the SHA256 hash of the unsigned payload
    :param hop_count: optional override of the target hop count
    :return: assembled bytes string containing a valid NSE protocol message
    :raises ValueError: for invalid RSA key input or when packing of structs failed
    """

    hop_count = hop_count or DEFAULT_HOP_COUNT
    proof_of_work_bits = proof_of_work_bits or DEFAULT_PROOF_OF_WORK_BITS
    if not rsa_key.has_private():
        raise ValueError(f"RSA key {rsa_key} doesn't contain a private part!")
    if rsa_key.size_in_bits() != 4096:
        raise ValueError(f"Only RSA keys of size 4096 bits are supported")
    proximity = proximity or calculate_proximity(rsa_key.public_key(), round_time)
    exported_public_key = rsa_key.public_key().export_key(format="DER")
    key_length = len(exported_public_key)

    # Calculate a hash collision for the header and the public key in DEM format (proof of work!)
    start = time.time()
    sample = -1
    hashed_header = None
    try:
        for sample in range(1 << 64):
            hashed_header = HASHED_HEADER.pack(key_length, proximity, round_time, sample) + exported_public_key
            if _check_proof_of_work(proof_of_work_bits, hashed_header):
                break
    except struct.error as exc:
        raise ValueError("Error packing the hashed header") from exc
    end = time.time()

    # Sign the relevant payload and return it
    if hashed_header is None or sample == -1:
        raise ValueError("Failed to calculate a hash collision. Invalid header configuration?")
    if logger is not None:
        logger.debug(f"Calculating message with {proof_of_work_bits}-bit hash collision took {end - start:.3f} seconds")
    sig = pss.new(rsa_key).sign(SHA512.new(hashed_header))
    try:
        header = PROTOCOL_HEADER.pack(HEADER_CODE, hop_count, key_length, proximity, round_time, sample)
    except struct.error as exc:
        raise ValueError("Error packing the protocol header") from exc
    return header + exported_public_key + sig


def unpack_message(msg: bytes, min_proximity: int = None, proof_of_work_bits: int = None) -> ProtocolMessage:
    """
    Unpack an incoming message as raw bytes string into a `ProtocolMessage` instance

    :param msg: raw bytes string that has been received as incoming NSE P2P message
    :param min_proximity: minimal proximity; messages with a lower proximity to the
        hash will be discarded before further checks of the content (e.g. signature
        and proof of work) to improve this function's performance
    :param proof_of_work_bits: optional indicator of the required bits of the proof of work hash
    :return: the unpacked message as a ProtocolMessage instance
    :raises ValueError: whenever something is wrong with the message, e.g. the
        signature is invalid, the proof of work hash is invalid or not large
        enough, the header has an invalid format, the message is too small
        or when the claimed proximity doesn't match the calculated proximity
    """

    min_proximity = min_proximity or 0
    proof_of_work_bits = proof_of_work_bits or DEFAULT_PROOF_OF_WORK_BITS
    if not isinstance(msg, bytes):
        raise TypeError(f"Invalid message type {type(msg)}, expected bytes")
    if len(msg) < 2 * SIGNATURE_LENGTH:
        raise ValueError("Message is too small, it can't hold all relevant data.")

    try:
        header_code, hop_count, pub_key_len, proximity, round_time, sample = PROTOCOL_HEADER.unpack(msg[:24])
    except struct.error as exc:
        raise ValueError("Invalid header format can't be unpacked") from exc
    if header_code != HEADER_CODE:
        raise ValueError(f"Invalid header code {msg[0]}, expected {HEADER_CODE}")
    if hop_count == 0:
        raise ValueError("Invalid hop count 0")
    if len(msg) != HEADER_LENGTH + pub_key_len + SIGNATURE_LENGTH:
        raise ValueError(f"Invalid public key length {pub_key_len} found in header")
    if min_proximity > proximity:
        raise ValueError(f"Message proximity {proximity} is smaller than minimum {min_proximity}")

    if not _check_proof_of_work(
            proof_of_work_bits,
            HASHED_HEADER.pack(pub_key_len, proximity, round_time, sample)
            + msg[HEADER_LENGTH:HEADER_LENGTH + pub_key_len]
    ):
        raise ValueError("Invalid ProofOfWork hash")
    try:
        signature = msg[-SIGNATURE_LENGTH:]
        pub_key = RSA.import_key(msg[HEADER_LENGTH:HEADER_LENGTH + pub_key_len])
        pss.new(pub_key).verify(SHA512.new(msg[2:-SIGNATURE_LENGTH]), signature)
    except IndexError as exc:
        raise ValueError from exc
    if calculate_proximity(pub_key, round_time) != proximity:
        raise ValueError(f"Calculated proximity doesn't match proximity {proximity}")

    return ProtocolMessage(public_key=pub_key, proximity=proximity, round_time=round_time)


if __name__ == "__main__":
    import random

    key = RSA.generate(4096)
    print("Generated 4096 bit RSA key.")
    t = random.randint(0, 65536) * random.randint(0, 65536) * random.randint(0, 65536)
    m = build_message(key, t)
    print(f"Message for round time={t} (len={len(m)}):\n{m}")
    print(f"Unpacked message: {unpack_message(m)}")
