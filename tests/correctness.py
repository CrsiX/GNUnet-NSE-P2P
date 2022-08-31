import os
import sys
import random
import string
import threading
import subprocess

from . import utils


class ConformanceTests(utils.GossipEnabledTests):
    def test_api_conformance(self):
        # TODO: Create an API subprocess that runs and will be called by the mockup client
        pass


class CorrectnessTests(utils.GossipEnabledTests):
    def setUp(self) -> None:
        super().setUp()
        self._running = False
        gossip = f"127.0.0.1:{self.gossip_port}"
        self.subprocesses = []
        self.count = 2  # random.randint(50, 100)

        for instance in range(self.count):
            key_file = f"private_key{instance:0>2}.pem"
            for p in [
                os.path.join(".", "private_keys", key_file),
                os.path.join(".", "tests", "private_keys", key_file),
                os.path.join(".", key_file)
            ]:
                if os.path.exists(p):
                    break
            else:
                self.fail(f"Private key file {key_file!r} not found!")

            port = random.randint(10000, 50000)
            while port in [e[0] for e in self.subprocesses]:
                port = random.randint(10000, 50000)
            db = f"sqlite:////tmp/nse_{''.join(random.choice(string.ascii_lowercase) for _ in range(16))}.db"
            process = subprocess.Popen(
                [sys.executable, "-m", "p2p_nse5", "run", "-l", f"127.0.0.1:{port}", "-p", p, "-d", db, "-g", gossip],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            self.subprocesses.append((port, p, db, process))
        self._running = True

    def test_correctness(self):
        # TODO: Create a bunch of subprocesses, each with other ports and keys and let them do their job,
        #  then query them for their size estimates (attention: test probably takes incredibly long!)
        self._shutdown()

    def _shutdown(self, inside: bool = True) -> None:
        def _terminate(process):
            process.terminate()
            try:
                process.wait(0.05)
            except subprocess.TimeoutExpired:
                process.kill()
                try:
                    process.wait(0.2)
                except subprocess.TimeoutExpired:
                    pass
            if not process.stdout.closed:
                process.stdout.close()
            if not process.stderr.closed:
                process.stderr.close()

        if hasattr(self, "subprocesses"):
            threads = []
            for port, path, db, proc in self.subprocesses:
                t = threading.Thread(target=_terminate, daemon=True, args=(proc,))
                if not inside:
                    print(port, path)
                    print(proc.stderr.read().decode("UTF-8"))
                    print(proc.stdout.read().decode("UTF-8"))
                t.start()
                threads.append(t)
            for t in threads:
                t.join()
        self._running = False

    def tearDown(self) -> None:
        if self._running:
            self._shutdown(inside=False)
        super().tearDown()
