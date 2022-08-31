import os
import sys
import random
import unittest
import subprocess


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
