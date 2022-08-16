#!/usr/bin/env python3

import os
import sys
import shutil
import asyncio
import logging.config

from . import config, utils, nse


def main() -> int:
    parser = utils.get_cli_parser()
    args = parser.parse_args()

    if args.command == "run":
        if not os.path.exists(args.config):
            parser.error(f"config file {args.config!r} not found, please use command 'config' to create one")
            return 2

        try:
            conf = config.load_configuration([args.config])
        except Exception:
            parser.print_usage(sys.stderr)
            raise

        log_conf = {
            "datefmt": conf.nse.log_dateformat,
            "format": conf.nse.log_format,
            "level": conf.nse.log_level,
            "style": conf.nse.log_style
        }
        if conf.nse.log_file not in ["", "-", "stdout", "stderr"]:
            log_conf["filename"] = conf.nse.log_file
        elif conf.nse.log_file == "stderr":
            log_conf["stream"] = sys.stderr
        elif conf.nse.log_file == "stdout":
            log_conf["stream"] = sys.stdout
        logging.basicConfig(**log_conf)

        try:
            asyncio.run(nse.Server(conf).run())
        except KeyboardInterrupt:
            logging.getLogger("nse").info("Exiting")

    elif args.command == "config":
        if not args.force and os.path.exists(args.config):
            parser.error(f"config file {args.config!r} already exists, force overwriting it with option '-f'")
            return 2
        shutil.copy(
            os.path.abspath(os.path.join(
                os.path.split(sys.modules["p2p_nse5"].__loader__.path)[0],
                config.DEFAULT_CONFIG_INI_PATH
            )),
            args.config
        )
        print(f"A new configuration file has been created as {args.config!r}.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
