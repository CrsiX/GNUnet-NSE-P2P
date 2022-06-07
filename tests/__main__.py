"""
P2P NSE5 unittest framework
"""

import unittest
from typing import Optional


class MainProgram(unittest.TestProgram):
    test: unittest.TestSuite = None

    def createTests(self, from_discovery: bool = ..., loader: Optional[unittest.loader.TestLoader] = ...) -> None:
        def get_suite() -> unittest.TestSuite:
            suite = unittest.TestSuite()
            # TODO: Use suite.addTests to add more tests
            return suite
        self.test = get_suite()


if __name__ == "__main__":
    MainProgram(catchbreak=True)
