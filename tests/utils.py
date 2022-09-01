import os
import sys
import random
import socket
import struct
import unittest
import subprocess
from typing import Any, Tuple

from p2p_nse5.protocols import api


def find_path(paths: list) -> str:
    """
    Find a valid existing path of the specified paths or raise a ValueError
    """

    for path in paths:
        if os.path.exists(path):
            return path
    raise ValueError(f"No file found for search paths {paths!r}")


def query_nse(address: Tuple[Any, ...]) -> (int, int):
    """
    Query a NSE service using the NSE_ESTIMATE packet and return the result or raise an exception
    """

    with socket.socket() as s:
        s.connect(address)
        s.send(b"\x00\x04\x02\x08")
        r = s.recv(12)
        size, t, peers, std_deviation = struct.unpack("!HHII", r)
        if size != 12:
            raise ValueError("Invalid message size")
        if t != api.MessageType.NSE_ESTIMATE:
            raise ValueError("Invalid message type")
        s.shutdown(socket.SHUT_RD)
    return peers, std_deviation


class GossipEnabledTests(unittest.TestCase):
    def setUp(self) -> None:
        self.gossip_port = random.randint(10000, 40000)
        for path in [
            os.path.join(".", "mockup", "gossip_mockup.py"),
            os.path.join(".", "tests", "mockup", "gossip_mockup.py"),
            os.path.join(".", "gossip_mockup.py")
        ]:
            if os.path.exists(path):
                break
        else:
            self.fail("Unable to find gossip mockup implementation! Adjust cwd or search paths.")

        self.gossip_process = subprocess.Popen(
            [sys.executable, path, "-p", str(self.gossip_port), "-a", "127.0.0.1"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        with self.assertRaises(subprocess.TimeoutExpired):
            self.gossip_process.wait(0.15)

    def tearDown(self) -> None:
        if hasattr(self, "gossip_process"):
            self.gossip_process.terminate()
            try:
                self.gossip_process.wait(0.05)
            except subprocess.TimeoutExpired:
                self.gossip_process.kill()
                try:
                    self.gossip_process.wait(0.1)
                except subprocess.TimeoutExpired:
                    pass
            if not self.gossip_process.stdout.closed:
                self.gossip_process.stdout.close()
            if not self.gossip_process.stderr.closed:
                self.gossip_process.stderr.close()
