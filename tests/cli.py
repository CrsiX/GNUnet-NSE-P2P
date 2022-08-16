import sys
import time
import socket
import unittest
import threading
import subprocess


class CLITests(unittest.TestCase):
    def test_is_app_runnable(self):
        p = subprocess.run([sys.executable, "-m", "p2p_nse5"], timeout=0.5, capture_output=True)
        self.assertEqual(p.returncode, 2)
        p = subprocess.run([sys.executable, "-m", "p2p_nse5", "-h"], timeout=0.5, capture_output=True)
        self.assertEqual(p.returncode, 0)
        self.assertIn("Network Size Estimation (NSE)", p.stdout.decode("UTF-8"))
        self.assertIn("Licensed under AGPLv3.", p.stdout.decode("UTF-8"))

    def test_app_runs_with_defaults(self):
        def _run_dummy_tcp_server(host, port, delay):
            server = socket.create_server((host, port))
            s, a = server.accept()
            time.sleep(delay)
            s.close()
            server.close()

        t = threading.Thread(target=_run_dummy_tcp_server, args=("localhost", 5000, 0.5))
        t.start()
        default = "p2p_nse5/static/default_configuration.ini"
        with self.assertRaises(subprocess.TimeoutExpired):
            subprocess.run([sys.executable, "-m", "p2p_nse5", "-c", default, "run"], timeout=0.5, capture_output=True)
        t.join()
