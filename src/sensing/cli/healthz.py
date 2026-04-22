#!/usr/bin/env python3
"""
Liveness のチェックを行います

Usage:
  sensing-healthz [-c CONFIG] [-d]

Options:
  -c CONFIG         : CONFIG を設定ファイルとして読み込んで実行します．[default: config.yaml]
  -d                : デバッグモードで動作します．
"""

import logging
import pathlib
import sys

import docopt
import my_lib.config
import my_lib.healthz
import my_lib.logger


def main():
    args = docopt.docopt(__doc__)

    config_file = args["-c"]
    debug_mode = args["-d"]

    my_lib.logger.init("hems.rasp-aqua", level=logging.DEBUG if debug_mode else logging.INFO)

    logging.info("Using config config: %s", config_file)
    config = my_lib.config.load(config_file)

    target_list = [
        my_lib.healthz.HealthzTarget(
            name=name,
            liveness_file=pathlib.Path(config["liveness"]["file"][name]),
            interval=config[name]["interval_sec"],
        )
        for name in ["sensing"]
    ]

    failed = my_lib.healthz.check_liveness_all(target_list)
    if not failed:
        logging.info("OK.")
        sys.exit(0)
    else:
        sys.exit(-1)


if __name__ == "__main__":
    main()
