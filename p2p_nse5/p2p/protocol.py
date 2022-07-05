import math
import time
import struct
import hashlib
import logging

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
DEFAULT_PROOF_OF_WORK_BITS = 19  # TODO: Check which number of PoW bits is sufficient for the network
HASH_ENDIAN = "big"


class ProtocolMessage:
    round_time: int
    proximity: int
    public_key: RSA.RsaKey

    def __init__(self, round_time: int, proximity: int, public_key: RSA.RsaKey):
        self.round_time = round_time
        self.proximity = proximity
        self.public_key = public_key

    def __repr__(self):
        return f"ProtocolMessage({', '.join(f'{k}={getattr(self, k)!r}' for k in dir(self) if not k.startswith('_'))})"


def build_message(
        rsa_key: RSA.RsaKey,
        proximity: int,
        round_time: int,
        logger: logging.Logger = None,
        proof_of_work_bits: int = None,
        hop_count: int = None
) -> bytes:
    hop_count = hop_count or DEFAULT_HOP_COUNT
    proof_of_work_bits = proof_of_work_bits or DEFAULT_PROOF_OF_WORK_BITS
    if not rsa_key.has_private():
        raise ValueError(f"RSA key {rsa_key} doesn't contain a private part!")

    exported_public_key = rsa_key.public_key().export_key(format="DER")
    key_length = len(exported_public_key)
    proof_of_work_bytes = math.ceil(proof_of_work_bits / 8)

    # Calculating a hash collision for the header and the public key in DEM format
    start = time.time()
    sample = -1
    hashed_header = None
    for sample in range(1 << 64):
        hashed_header = HASHED_HEADER.pack(key_length, proximity, round_time, sample) + exported_public_key
        h = hashlib.sha256(hashed_header).digest()
        if int.from_bytes(h[-proof_of_work_bytes:], HASH_ENDIAN) % (1 << proof_of_work_bits) == 0:
            break
    end = time.time()

    # Signing the relevant payload and return it
    if hashed_header is None or sample == -1:
        raise RuntimeError("Failed to calculate a hash collision. Invalid header configuration?")
    if logger is not None:
        logger.debug(f"Calculating message with {proof_of_work_bits}-bit hash collision took {end-start:.3f} seconds")
    sig = pss.new(rsa_key).sign(SHA512.new(hashed_header))
    return PROTOCOL_HEADER.pack(b"*", hop_count, key_length, proximity, round_time, sample) + exported_public_key + sig


if __name__ == "__main__":
    k = RSA.generate(4096)
    print("Generated 4096 bit RSA key.")
    p = 42
    t = 1337
    print(f"Message for proximity={p} and round time={t}:\n{build_message(k, p, t)}")
