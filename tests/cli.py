import sys
import unittest
import subprocess


class CLITests(unittest.TestCase):
    def test_is_app_runnable(self):
        p = subprocess.run([sys.executable, "-m", "p2p_nse5"], timeout=0.5, capture_output=True)
        self.assertEqual(p.returncode, 2)
        p = subprocess.run([sys.executable, "-m", "p2p_nse5", "-h"], timeout=0.5, capture_output=True)
        self.assertEqual(p.returncode, 0)
        self.assertIn("Network Size Estimation (NSE)", p.stdout.decode("UTF-8"))
        self.assertIn("Licensed under AGPLv3.", p.stdout.decode("UTF-8"))
