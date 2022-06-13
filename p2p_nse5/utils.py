"""
Module with various different utilities
"""

import argparse

from . import config


def get_cli_parser() -> argparse.ArgumentParser:
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
    config_parser = commands.add_parser("config")
    config_parser.add_argument("-f", "--force", action="store_true", help="allow overwriting existing files")
    return parser
