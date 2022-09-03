import os
import sys
import random
import string
import unittest
import threading
import subprocess

from p2p_nse5.config import DEFAULT_CONFIG_FILE

from . import utils


class CLITests(unittest.TestCase):
    def test_is_app_runnable(self):
        p = subprocess.run([sys.executable, "-m", "p2p_nse5"], timeout=1.0, capture_output=True)
        self.assertEqual(p.returncode, 2)
        p = subprocess.run([sys.executable, "-m", "p2p_nse5", "-h"], timeout=1.0, capture_output=True)
        self.assertEqual(p.returncode, 0)
        self.assertIn(b"Network Size Estimation (NSE)", p.stdout)
        self.assertIn(b"Licensed under AGPLv3.", p.stdout)

    def test_app_runs_with_defaults(self):
        config = utils.find_path([os.path.join(".", DEFAULT_CONFIG_FILE), os.path.join("..", DEFAULT_CONFIG_FILE)])
        t = threading.Thread(target=utils.run_dummy_tcp_server, args=("localhost", 5000, 0.5), daemon=True)
        t.start()
        with self.assertRaises(subprocess.TimeoutExpired):
            subprocess.run(
                [sys.executable, "-m", "p2p_nse5", "run", "-c", config],
                timeout=0.75,
                capture_output=True
            )
        t.join()

    def test_app_runs_with_new(self):
        t = threading.Thread(target=utils.run_dummy_tcp_server, args=("localhost", 5000, 0.5), daemon=True)
        t.start()
        config = f"/tmp/nse_test_{''.join(random.choice(string.ascii_lowercase) for _ in '_' * 12)}.db"
        ret = subprocess.run([sys.executable, "-m", "p2p_nse5", "new", "-c", config], capture_output=True).returncode
        self.assertEqual(0, ret)
        with self.assertRaises(subprocess.TimeoutExpired):
            subprocess.run(
                [sys.executable, "-m", "p2p_nse5", "run", "-c", config],
                timeout=0.75,
                capture_output=True
            )
        t.join()
