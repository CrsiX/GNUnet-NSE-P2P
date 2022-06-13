"""
Configuration parser module
"""

import os
import configparser

import pydantic

DEFAULT_SECTION = "_default"
GLOBAL_SECTION = "global"
DEFAULT_CONFIG_FILE = "config.ini"
DEFAULT_CONFIG_INI_PATH = os.path.join("static", "default_configuration.ini")


class GossipConfiguration(pydantic.BaseModel):
    pass


class NSEConfiguration(pydantic.BaseModel):
    pass


class Configuration(pydantic.BaseModel):
    host_key_file: str
    gossip: GossipConfiguration
    nse: NSEConfiguration


def load_configuration(filenames: list[str]) -> Configuration:
    """
    Load a :class:`Configuration` object from a list of INI-style config files

    In case the configuration file contains top-level entries without prior
    section, those entries are listed below a global section :var:`GLOBAL_SECTION`.

    :param filenames: list of filenames to search for
    :return: instance of a :class:`Configuration`
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
