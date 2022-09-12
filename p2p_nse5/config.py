"""
Configuration parser module
"""

import os
import configparser

import pydantic
import Crypto.PublicKey.RSA

from . import persistence, utils
from .protocols import p2p


DEFAULT_SECTION = "_default"
GLOBAL_SECTION = "global"
DEFAULT_CONFIG_FILE = "default_configuration.ini"
DEFAULT_CONFIG_INI_PATH = os.path.join(".", "default_configuration.ini")


class GossipConfiguration(pydantic.BaseModel):
    """
    Gossip configuration
    """

    api_address: str
    """API address of the Gossip server (usually localhost)"""

    @pydantic.validator("api_address")
    def is_valid_address_and_port(value: str):  # noqa
        """
        Checks :attr:`api_address` for conformance with :func:`p2p_nse5.utils.split_ip_address_and_port`

        :raise ValueError: if it's not valid
        """

        utils.split_ip_address_and_port(value, True)
        return value


class NSEConfiguration(pydantic.BaseModel):
    """Configuration specific to the NSE module"""

    api_address: str
    """API address the NSE module should be listening on (usually localhost)"""

    data_type: int = 31337
    """Data type used by Gossip to identify the NSE messages"""

    data_gossip_ttl: int = 64
    """TTL used to instruct Gossip how far NSE messages should be spread in the network"""

    enforce_localhost: bool = True
    """Switch to enforce incoming API connections to originate from localhost"""

    log_file: str = "-"  # also supports stdout and stderr
    log_level: str = "DEBUG"
    log_style: str = "{"
    log_format: str = "{asctime}: [{levelname:<8}] {name}: {message}"
    log_dateformat: str = "%d.%m.%Y %H:%M:%S"

    database: str = persistence.DEFAULT_DATABASE_URL
    """Connection string to the database used in the project"""

    frequency: int = 1800
    """Length of a single NSE round in seconds"""
    respected_rounds: int = 8
    """Number of rounds to use in the calculation of the approx. net size"""
    max_backlog_rounds: int = 2
    """Max number of rounds we accept future packets for"""
    proof_of_work_bits: int = p2p.DEFAULT_PROOF_OF_WORK_BITS
    """Number of bits required for the proof of work in P2P messages"""

    @pydantic.validator("api_address")
    def is_valid_address_and_port(value: str):  # noqa
        """
        Checks :attr:`api_address` for conformance with :func:`p2p_nse5.utils.split_ip_address_and_port`

        :raise ValueError: if it's not valid
        """

        utils.split_ip_address_and_port(value, True)
        return value

    @pydantic.validator("data_type")
    def is_valid_data_type_for_gossip_api(value: str):  # noqa
        """
        Checks :attr:`data_type` to be in range 1 - 65535

        :raise ValueError: if it's not in that range
        """

        if not 1 <= int(value) < 65536:
            raise ValueError(f"Data type value {value} out of range for uint16")
        return value


class Configuration(pydantic.BaseModel):
    hostkey: str  # noqa
    """Path to the RSA 4096-bit private key in PEM format"""
    gossip: GossipConfiguration
    nse: NSEConfiguration
    _host_key: Crypto.PublicKey.RSA.RsaKey = None

    @property
    def private_key(self) -> Crypto.PublicKey.RSA.RsaKey:
        """:class:`Crypto.PublicKey.RSA.RsaKey` instance of the private key"""
        if self._host_key is None:
            self._reload_key()
        return self._host_key

    @property
    def public_key(self) -> Crypto.PublicKey.RSA.RsaKey:
        """:class:`Crypto.PublicKey.RSA.RsaKey` instance of the public key"""
        if self._host_key is None:
            self._reload_key()
        return self._host_key.public_key()

    def _reload_key(self):
        with open(self.hostkey, "r") as f:
            content = f.read()
        # Note that the unencrypted RSA private key is kept in memory here!
        self._host_key = Crypto.PublicKey.RSA.import_key(content)

    class Config:
        arbitrary_types_allowed: bool = True
        underscore_attrs_are_private: bool = True


def load(filenames: list[str]) -> Configuration:
    """
    Load a :class:`Configuration` object from a list of INI-style config files

    In case the configuration file contains top-level entries without prior
    section, those entries are listed below a global section :const:`GLOBAL_SECTION`.

    :param filenames: list of filenames to search for
    :return: instance of a :class:`Configuration`
    :raise RuntimeError: if no configuration file was found in the list of files
    """

    def make_conf(c: configparser.ConfigParser) -> Configuration:
        data = dict(c[GLOBAL_SECTION])
        data.update({k: dict(v) for k, v in c.items() if k != DEFAULT_SECTION and k != GLOBAL_SECTION})
        try:
            return Configuration(**data)
        except Exception as err:
            raise err from None

    try:
        config = configparser.ConfigParser(default_section=DEFAULT_SECTION)
        config.read(filenames)
        return make_conf(config)
    except configparser.MissingSectionHeaderError as exc:
        for filename in filenames:
            if not os.path.exists(filename):
                continue
            with open(filename) as f:
                content = f.read()
            config = configparser.ConfigParser(default_section=DEFAULT_SECTION)
            config.read_string(f"[{GLOBAL_SECTION}]{os.linesep}{content}", filename)
            return make_conf(config)
        raise RuntimeError("No configuration file found") from exc
