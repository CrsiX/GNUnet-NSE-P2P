"""
Module with various different utilities
"""

import socket
import argparse
from typing import Tuple

import pydantic

from . import config


def counter(start: int = 0):
    n = start
    while True:
        n += 1
        yield n


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


def split_ip_address_and_port(value: str) -> Tuple[socket.AddressFamily, str, int]:
    """
    Validate that a given string conforms to the specific IP and port layout
    and split it into address family, IP address string and port number

    This layout uses `{ipv4}:{port}` or `[{ipv6}]:{port}`.

    :param value: string to check for layout validity
    :return: a tuple of the address family (either IPv4 or IPv6),
        the IP address as a string and the port number as integer
    :raises ValueError: when the string is not conform to the layout
    """

    if ":" not in value:
        raise ValueError("Missing ':'")
    port = int(value[value.rfind(":") + 1:])
    if not 0 < port < 65536:
        raise ValueError("Invalid port")
    if value.startswith("[") and "]:" in value:
        ip = value[1:value.rfind("]")]
        if pydantic.IPvAnyAddress().validate(ip).version != 6:
            raise ValueError("Invalid IPv6 address")
        return socket.AF_INET6, ip, port
    else:
        ip = value[:value.rfind(":")]
        if pydantic.IPvAnyAddress().validate(ip).version != 4:
            raise ValueError("Invalid IPv4 address")
        return socket.AF_INET, ip, port
