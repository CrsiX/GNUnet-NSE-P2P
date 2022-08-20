"""
Module with various different utilities
"""

import socket
import argparse
import ipaddress
from typing import Tuple

import pydantic

from . import config


def counter(start: int = 0):
    n = start
    while True:
        n += 1
        yield n


def get_cli_parser() -> argparse.ArgumentParser:
    def add_conf_option(p: argparse.ArgumentParser) -> argparse.ArgumentParser:
        p.add_argument(
            "-c", "--conf",
            help=f"configuration filename (defaults to {config.DEFAULT_CONFIG_FILE!r})",
            dest="config",
            default=config.DEFAULT_CONFIG_FILE,
            metavar="<file>"
        )
        return p

    parser = argparse.ArgumentParser(
        prog="p2p_nse5",
        description="API for handling Network Size Estimation (NSE) based on GNUnet NSE algorithm for P2P applications",
        epilog="Licensed under AGPLv3."
    )
    commands = parser.add_subparsers(title="commands", dest="command", required=True)

    parser_run = add_conf_option(commands.add_parser("run", help="execute the program running the NSE module"))
    parser_run.add_argument("-l", "--listen", type=int, help="overwrite local API listen address")

    parser_new = add_conf_option(commands.add_parser(
        "new",
        help="create a new configuration file (for a new program instance)"
    ))
    parser_new.add_argument("-f", "--force", action="store_true", help="allow overwriting existing files")

    add_conf_option(commands.add_parser(
        "validate",
        help="validate the configuration file by showing the parsed values incl. defaults "
             "but excluding all irrelevant options (possibly from other modules)"
    ))

    return parser


def split_ip_address_and_port(value: str, require_localhost: bool = False) -> Tuple[socket.AddressFamily, str, int]:
    """
    Validate that a given string conforms to the specific IP and port layout
    and split it into address family, IP address string and port number

    This layout uses `{ipv4}:{port}` or `[{ipv6}]:{port}`.

    :param value: string to check for layout validity
    :param require_localhost: switch to enforce a IPv4 or IPv6 localhost address
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
        if require_localhost and not ipaddress.IPv6Address(ip).is_loopback:
            raise ValueError(f"IPv6 {ip} is no address of localhost")
        return socket.AF_INET6, ip, port
    else:
        ip = value[:value.rfind(":")]
        if pydantic.IPvAnyAddress().validate(ip).version != 4:
            raise ValueError("Invalid IPv4 address")
        if require_localhost and not ipaddress.IPv4Address(ip).is_loopback:
            raise ValueError(f"IPv4 {ip} is no address of localhost")
        return socket.AF_INET, ip, port
