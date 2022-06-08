"""
P2P NSE5 unittest framework
"""

import unittest
from typing import Optional


TEST_CLASSES = []


class MainProgram(unittest.TestProgram):
    test: unittest.TestSuite = None

    def createTests(self, from_discovery: bool = ..., loader: Optional[unittest.loader.TestLoader] = ...) -> None:
        def get_suite() -> unittest.TestSuite:
            suite = unittest.TestSuite()
            for test_cls in TEST_CLASSES:
                for fixture in filter(lambda f: f.startswith("test_"), dir(test_cls)):
                    suite.addTest(test_cls(fixture))
            return suite
        self.test = get_suite()


if __name__ == "__main__":
    MainProgram(catchbreak=True)
