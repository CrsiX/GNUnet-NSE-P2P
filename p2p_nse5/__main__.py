#!/usr/bin/env python3

import os
import sys
import argparse

from . import config


def main() -> int:
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
        metavar="<file>"
    )

    commands = parser.add_subparsers(title="commands", dest="command", required=True)
    commands.add_parser("run")
    commands.add_parser("config")

    args = parser.parse_args()
    if not os.path.exists(args.config):
        parser.error(f"config file {args.config!r} not found, please use command 'config' to create one")
        return 2

    return 0


if __name__ == "__main__":
    sys.exit(main())
