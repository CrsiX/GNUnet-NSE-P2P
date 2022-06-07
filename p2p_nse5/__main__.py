#!/usr/bin/env python3

import argparse
import os

from . import config


def main() -> int:
    def existing_filename(arg: str) -> str:
        if os.path.exists(arg):
            return arg
        raise ValueError(f"File not found: {arg!r}")

    parser = argparse.ArgumentParser(
        prog="p2p_nse5",
        description=__doc__,
        epilog="Licensed under AGPLv3."
    )
    parser.add_argument(
        "-c",
        help=f"configuration filename (defaults to {config.DEFAULT_CONFIG_FILE!r})",
        dest="config",
        default=config.DEFAULT_CONFIG_FILE,
        type=existing_filename,
        metavar="<file>"
    )
    parser.parse_args()

    return 0


if __name__ == "__main__":
    exit(main())
