"""
Configuration parser module
"""

import os
import configparser

DEFAULT_SECTION = "_default"
GLOBAL_SECTION = "_global"
DEFAULT_CONFIG_FILE = "config.ini"


def load_configuration(filenames: list[str]) -> dict[str, dict[str, str]]:
    """
    Load a dictionary-based configuration from a list of INI-style config files

    In case the configuration file contains top-level entries without prior
    section, those entries are listed below a global section :var:`GLOBAL_SECTION`.

    :param filenames: list of filenames to search for
    :return: dictionary of sections of key-value pairs
    """

    try:
        config = configparser.ConfigParser(default_section=DEFAULT_SECTION)
        config.read(filenames)
        return {k: dict(v) for k, v in config.items() if k != DEFAULT_SECTION}
    except configparser.MissingSectionHeaderError:
        for filename in filenames:
            if not os.path.exists(filename):
                continue
            with open(filename) as f:
                content = f.read()
            config = configparser.ConfigParser(default_section=DEFAULT_SECTION)
            config.read_string(f"[{GLOBAL_SECTION}]{os.linesep}{content}", filename)
            return {k: dict(v) for k, v in config.items() if k != DEFAULT_SECTION}
        else:
            raise RuntimeError("No configuration file found")
