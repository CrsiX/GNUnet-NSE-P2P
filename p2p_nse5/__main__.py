#!/usr/bin/env python3

import os
import sys
import json
import shutil
import argparse

from . import config, entrypoint, utils


def _run(parser: argparse.ArgumentParser, args: argparse.Namespace) -> int:
    if not os.path.exists(args.config):
        parser.error(f"config file {args.config!r} not found, please use command 'config' to create one")
        return 2

    try:
        conf = config.load([args.config])
    except Exception:
        parser.print_usage(sys.stderr)
        raise

    if args.database:
        conf.nse.database = args.database
    if args.gossip:
        conf.gossip.api_address = args.gossip
    if args.listen:
        conf.nse.api_address = args.listen
    if args.private_key:
        conf.hostkey = args.private_key
    entrypoint.start(conf)
    return 0


def _validate(parser: argparse.ArgumentParser, args: argparse.Namespace) -> int:
    if not os.path.exists(args.config):
        parser.error(f"config file {args.config!r} not found, please use command 'config' to create one")
        return 2

    try:
        conf = config.load([args.config])
        print(json.dumps(conf.dict(), indent=4, sort_keys=True))
    except Exception:
        parser.print_usage(sys.stderr)
        raise
    return 0


def _new(parser: argparse.ArgumentParser, args: argparse.Namespace) -> int:
    if not args.force and os.path.exists(args.config):
        parser.error(f"config file {args.config!r} already exists, force overwriting it with option '-f'")
        return 2
    for source in [
        config.DEFAULT_CONFIG_INI_PATH,
        os.path.abspath(os.path.join(
            os.path.split(sys.modules["p2p_nse5"].__loader__.path)[0],
            config.DEFAULT_CONFIG_INI_PATH
        ))
    ]:
        if os.path.exists(source):
            shutil.copy(source, args.config)
            print(f"A new configuration file has been created as {args.config!r}.")
            break
    else:
        print("ERROR: No default configuration file found. Please get a new copy of this project!", file=sys.stderr)
        return 1


def main() -> int:
    parser = utils.get_cli_parser()
    args = parser.parse_args()

    return {
        "run": _run,
        "validate": _validate,
        "new": _new
    }[args.command](parser, args)


if __name__ == "__main__":
    sys.exit(main())
