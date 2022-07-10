"""
Module with various different utilities
"""

import argparse

import pydantic

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


def validate_ip_address_and_port(value: str) -> str:
    """
    Validate that a given string conforms to the specific IP and port layout

    This layout uses `{ipv4}:{port}` or `[{ipv6}]:{port}`.

    :param value: string to check for layout validity
    :return: the same, un-changed string
    :raises ValueError: when the string is not conform to the layout
    """

    if ":" not in value:
        raise ValueError("Missing ':'")
    if not 0 < int(value[value.rfind(":")+1:]) < 65536:
        raise ValueError("Invalid port")
    if value.startswith("[") and "]:" in value:
        if pydantic.IPvAnyAddress().validate(value[1:value.rfind("]")]).version != 6:
            raise ValueError("Invalid IPv6 address")
    else:
        if pydantic.IPvAnyAddress().validate(value[:value.rfind(":")]).version != 4:
            raise ValueError("Invalid IPv4 address")
    return value
