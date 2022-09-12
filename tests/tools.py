import random
import unittest

import Crypto.PublicKey.RSA

from p2p_nse5.utils import get_std_deviation
from p2p_nse5.protocols import p2p


class ToolTests(unittest.TestCase):
    def test_std_deviation(self):
        self.assertEqual(0, get_std_deviation([]))
        self.assertEqual(0, get_std_deviation([1337]))
        self.assertEqual(0, get_std_deviation([1337, 1337]))
        self.assertEqual(0, get_std_deviation([1337, 1337, 1337]))
        self.assertEqual(0, get_std_deviation([42, 42, 42]))
        self.assertEqual(2, get_std_deviation([1, 2, 3, 4, 5, 6, 7]))
        self.assertEqual(5, get_std_deviation([10, 12, 23, 23, 16, 23, 21, 16]))
        self.assertEqual(2, get_std_deviation([2, 4, 4, 4, 5, 5, 7, 9]))
        self.assertEqual(10, get_std_deviation([154, 161, 172, 173, 181]))
        self.assertEqual(5905, get_std_deviation([5, 6, 2834, 28, 129, 1927, 918, 19273, 23]))
        self.assertEqual(208, get_std_deviation([52, 634, 9, 19, 375, 197, 98, 26]))

    def test_invalid_key(self):
        rsa_key = Crypto.PublicKey.RSA.generate(1024)
        self.assertTrue(rsa_key.has_private())
        with self.assertRaises(ValueError):
            p2p.build_message(rsa_key, 1337)

    def test_p2p_message(self):
        rsa_key = Crypto.PublicKey.RSA.generate(4096)
        with self.assertRaises(ValueError):
            p2p.build_message(rsa_key.public_key(), 1337)

        for _ in range(4):
            for prefix in range(20):
                v = random.randint(1, 2**20)
                p = p2p.calculate_proximity(rsa_key, v)
                msg = p2p.build_message(rsa_key, v, proximity=p, proof_of_work_bits=prefix)
                self.assertGreater(len(msg), 1024)
                protocol_message = p2p.unpack_message(msg, proof_of_work_bits=prefix)
                self.assertEqual(protocol_message.public_key.n, rsa_key.n)
                self.assertEqual(protocol_message.proximity, p)
                self.assertEqual(protocol_message.round_time, v)
