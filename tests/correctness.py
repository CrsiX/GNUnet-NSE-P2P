import os
import sys
import time
import random
import string
import subprocess

from p2p_nse5.persistence import init, get_new_session, Peer, Round

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
        self._count = min(100, random.randint(5, 10) * os.cpu_count())
        return self._count

    @staticmethod
    def _wait_for_subprocesses():
        queue = []
        while queue:
            p = queue.pop(0)
            try:
                utils.query_nse(("127.0.0.1", p))
            except ConnectionRefusedError:
                queue.append(p)
                time.sleep(0.05)

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


class SingleTests(NSETests):
    def setUp(self) -> None:
        self._count = 1
        super().setUp()

    @staticmethod
    def _add(round_id, proximity, peer_id):
        with get_new_session() as session:
            session.add(Round(round=round_id, proximity=proximity, peer_id=peer_id))
            session.commit()

    def test_valid_responses(self):
        self._wait_for_subprocesses()
        db = self.subprocesses[0][2]
        self.assertEqual((0, 0), utils.query_nse(("127.0.0.1", self.subprocesses[0][0])))
        init(db, False)
        with get_new_session() as session:
            session.add(Peer(public_key=b"foo", interactions=0))
            session.add(Peer(public_key=b"bar", interactions=0))
            session.add(Peer(public_key=b"baz", interactions=0))
            session.commit()
        self._add(0, 2, 1)
        self.assertEqual((3, 0), utils.query_nse(("127.0.0.1", self.subprocesses[0][0])))
        self._add(1, 2, 2)
        self.assertEqual((6, 0), utils.query_nse(("127.0.0.1", self.subprocesses[0][0])))
        self._add(2, 0, 2)
        self.assertEqual((7, 1), utils.query_nse(("127.0.0.1", self.subprocesses[0][0])))
        self._add(3, 4, 3)
        self.assertEqual((20, 1), utils.query_nse(("127.0.0.1", self.subprocesses[0][0])))

    def test_simple_responses(self):
        self._wait_for_subprocesses()
        db = self.subprocesses[0][2]
        self.assertEqual((0, 0), utils.query_nse(("127.0.0.1", self.subprocesses[0][0])))
        init(db, False)
        with get_new_session() as session:
            session.add(Peer(public_key=b"foo", interactions=0))
            session.commit()
        for i in [(0, 2), (1, 3), (2, 5), (3, 6), (4, 8)]:
            self._add(i[0], 1, 1)
            self.assertEqual((i[1], 0), utils.query_nse(("127.0.0.1", self.subprocesses[0][0])))


class ExecutionTests(NSETests):
    def test_execution(self):
        self._wait_for_subprocesses()
        for port in [e[0] for e in self.subprocesses]:
            self.assertEqual((0, 0), utils.query_nse(("127.0.0.1", port)))
