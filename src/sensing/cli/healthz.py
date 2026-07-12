#!/usr/bin/env python3
"""
Liveness のチェックを行います

Usage:
  sensing-healthz [-c CONFIG] [-D]

Options:
  -c CONFIG         : CONFIG を設定ファイルとして読み込んで実行します。[default: config.yaml]
  -D                : デバッグモードで動作します。
"""

from __future__ import annotations

import logging
import pathlib
import sys

import docopt
import my_lib.config
import my_lib.healthz
import my_lib.logger

import sensing


def main() -> None:
    args = docopt.docopt(__doc__)

    config_file = args["-c"]
    debug_mode = args["-D"]

    my_lib.logger.init("sensing-healthz", level=logging.DEBUG if debug_mode else logging.INFO)

    logging.info("Using config: %s", config_file)
    config = my_lib.config.load(config_file, sensing.get_schema_path())

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
        sys.exit(1)


if __name__ == "__main__":
    main()
