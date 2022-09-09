import os
import sys
import time
import random
import string
import subprocess

from . import utils


class NSETests(utils.GossipEnabledTests):
    @property
    def config_path(self) -> str:
        if hasattr(self, "_config_path"):
            return self._config_path
        self._config_path = utils.find_path([
            os.path.join(".", "default_configuration.ini"),
            os.path.join("..", "default_configuration.ini"),
            os.path.join("..", "p2p_nse5", "default_configuration.ini")
        ])
        return self._config_path

    @property
    def count(self) -> int:
        if hasattr(self, "_count"):
            return self._count
        self._count = random.randint(5, 10) * os.cpu_count()
        return self._count

    def setUp(self) -> None:
        super().setUp()
        self._running = False
        c = self.config_path
        g = f"127.0.0.1:{self.gossip_port}"
        self.subprocesses = []

        for instance in range(self.count):
            key_file = f"private_key{instance:0>2}.pem"
            path = utils.find_path([
                os.path.join(".", "private_keys", key_file),
                os.path.join(".", "tests", "private_keys", key_file),
                os.path.join(".", key_file)
            ])

            port = random.randint(10000, 50000)
            while port in [e[0] for e in self.subprocesses]:
                port = random.randint(10000, 50000)
            listen = f"127.0.0.1:{port}"
            db = f"sqlite:////tmp/nse_{''.join(random.choice(string.ascii_lowercase) for _ in range(16))}.db"
            process = subprocess.Popen(
                [sys.executable, "-m", "p2p_nse5", "run", "-l", listen, "-p", path, "-c", c, "-d", db, "-g", g],
                stdout=sys.stdout,
                stderr=subprocess.PIPE
            )
            self.subprocesses.append((port, path, db, process))
        time.sleep(max(self.count / os.cpu_count(), 1.0))
        self._running = True

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
            if process.stdout is not None and not process.stdout.closed:
                if not inside:
                    print(proc.stdout.read().decode("UTF-8"))
                process.stdout.close()
            if process.stderr is not None and not process.stderr.closed:
                if not inside:
                    print(proc.stderr.read().decode("UTF-8"))
                process.stderr.close()

        if hasattr(self, "subprocesses"):
            for port, path, db, proc in self.subprocesses:
                _terminate(proc)
        self._running = False

    def tearDown(self) -> None:
        if self._running:
            self._shutdown(inside=False)
        super().tearDown()


class CorrectnessTests(NSETests):
    def setUp(self) -> None:
        self._config_path = utils.find_path([
            os.path.join(".", "tests", "static", "correctness-tests.ini"),
            os.path.join("tests", "static", "correctness-tests.ini"),
            os.path.join("..", "tests", "static", "correctness-tests.ini"),
            os.path.join("static", "correctness-tests.ini"),
            os.path.join("..", "static", "correctness-tests.ini")
        ])
        super().setUp()

    def test_correctness(self):
        # TODO: Create a bunch of subprocesses, each with other ports and keys and let them do their job,
        #  then query them for their size estimates (attention: test probably takes incredibly long!)
        self._shutdown()


class ExecutionTests(NSETests):
    def test_execution(self):
        for port in [e[0] for e in self.subprocesses]:
            utils.query_nse(("127.0.0.1", port))
