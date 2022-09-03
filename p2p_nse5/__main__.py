#!/usr/bin/env python3

import os
import sys
import json
import random
import string

from . import config, entrypoint, utils


def main() -> int:
    parser = utils.get_cli_parser()
    args = parser.parse_args()

    if args.command == "run":
        if not os.path.exists(args.config):
            parser.error(f"config file {args.config!r} not found, please use command 'config' to create one")
            return 2

        try:
            conf = config.load([args.config])
        except Exception:
            parser.print_usage(sys.stderr)
            raise

        if args.listen:
            conf.nse.api_address = args.listen
        entrypoint.start(conf)

    elif args.command == "validate":
        if not os.path.exists(args.config):
            parser.error(f"config file {args.config!r} not found, please use command 'config' to create one")
            return 2

        try:
            conf = config.load([args.config])
            print(json.dumps(conf.dict(), indent=4, sort_keys=True))
        except Exception:
            parser.print_usage(sys.stderr)
            raise

    elif args.command == "new":
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
                with open(source, "r") as f:
                    content = f.read()
                content = content.replace(
                    "database = sqlite:///./nse.db",
                    f"database = sqlite:///./nse_{''.join(random.choice(string.ascii_lowercase) for _ in '_' * 8)}.db"
                )
                with open(args.config, "w") as f:
                    f.write(content)
                print(f"A new configuration file has been created as {args.config!r}.")
                break
        else:
            print("ERROR: No default configuration file found. Please get a new copy of this project!", file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main())
