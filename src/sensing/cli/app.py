#!/usr/bin/env python3
"""
I2C/SPI/UART で接続されたセンサーで計測を行い、結果を Fluentd で送信するスクリプトです。

Usage:
  sensing [-c CONFIG] [-D]
  sensing --list [-c CONFIG] [-D]
  sensing --once [-c CONFIG] [-D]
  sensing --check-config [-c CONFIG]

Options:
  -c CONFIG         : CONFIG を設定ファイルとして読み込んで実行します。[default: config.yaml]
  --list            : 設定された全センサーを ping して一覧表示します (計測はしません)。
  --once            : 1 周期だけ計測して結果を表示します (Fluentd への送信や Liveness 更新はしません)。
  --check-config    : 設定ファイルを検証して終了します (0: OK, 1: NG)。
  -D                : デバッグモードで動作します。
"""

from __future__ import annotations

import logging
import os
import pathlib
import signal
import socket
import sys
import threading
import time
from typing import Any

import docopt
import my_lib.config
import my_lib.fluentd_util
import my_lib.footprint
import my_lib.logger
import my_lib.notify.slack
import my_lib.sensor

import sensing
import sensing.spool

# センサーの計測がこの回数連続で失敗したら通知し、inactive に降格する
FAIL_THRESHOLD = 2

# NOTE: time.sleep() と違い、シグナルハンドラから即座に解除できる (PEP 475 対策)
should_terminate = threading.Event()


def sig_handler(num: int, _frame: Any) -> None:
    logging.warning("receive signal %d", num)

    if num in (signal.SIGTERM, signal.SIGINT):
        should_terminate.set()


def notify_failed(slack_config: Any, hostname: str, failed: my_lib.sensor.FailedSensor) -> None:
    my_lib.notify.slack.error(
        slack_config,
        f"sensing ({failed.sensor.NAME})",
        f"{my_lib.sensor.sensor_info(failed.sensor)} on {hostname}\n\n{failed.traceback}",
    )


def notify_recovered(slack_config: Any, hostname: str, sensor: Any) -> None:
    message = f"{my_lib.sensor.sensor_info(sensor)} on {hostname} が復帰しました"
    logging.info(message)

    # NOTE: info チャンネルが設定されている場合のみ Slack にも復帰通知を送る
    info_config = getattr(slack_config, "info", None)
    if info_config is not None and info_config.channel.name:
        my_lib.notify.slack.info(slack_config, f"sensing ({sensor.NAME})", message)


def build_meta(
    hostname: str,
    elapsed_sec: float,
    is_success: bool,
    active_sensor_list: list[Any],
    inactive_sensor_list: list[Any],
    spool_count: int,
) -> dict[str, Any]:
    """欠測をダッシュボード側で判別できるようにするための計測メタデータ。"""
    return {
        "hostname": hostname,
        "elapsed_sec": round(elapsed_sec, 3),
        "success": is_success,
        "sensor_active": len(active_sensor_list),
        "sensor_inactive": len(inactive_sensor_list),
        "sensor_inactive_names": ",".join(sensor.NAME for sensor in inactive_sensor_list),
        "spool_count": spool_count,
    }


def create_spool(config: dict[str, Any]) -> sensing.spool.Spool | None:
    spool_file = config["fluentd"].get("spool_file")
    if spool_file is None:
        return None

    spool_path = pathlib.Path(spool_file)
    if not spool_path.is_absolute():
        spool_path = pathlib.Path(config["base_dir"]) / spool_path

    return sensing.spool.Spool(spool_path, max_mb=config["fluentd"].get("spool_max_mb", 10.0))


def execute(config: dict[str, Any], once: bool = False) -> None:  # noqa: C901, PLR0915
    sensor_list = my_lib.sensor.load(config["sensor"])

    active_sensor_list, inactive_sensor_list = my_lib.sensor.ping(sensor_list)
    retry_index = 0

    hostname = os.environ.get("NODE_HOSTNAME", socket.gethostname())
    logging.info("Hostname: %s", hostname)

    interval_sec = config["sensing"]["interval_sec"]
    fluentd_label = config["fluentd"].get("data_label", "rasp")

    sender = None
    spool = None
    slack_config: Any = my_lib.notify.slack.SlackEmptyConfig()
    if not once:
        sender = my_lib.fluentd_util.get_handle(
            config["fluentd"].get("tag", "sensor"),
            host=config["fluentd"]["host"],
            port=config["fluentd"].get("port", 24224),
        )
        spool = create_spool(config)
        slack_config = my_lib.notify.slack.SlackConfig.parse(config.get("slack", {}))

    signal.signal(signal.SIGTERM, sig_handler)
    signal.signal(signal.SIGINT, sig_handler)

    try:
        while True:
            time_start = time.time()
            logging.info("Start.")

            retry_index, revived = my_lib.sensor.retry_inactive(
                active_sensor_list, inactive_sensor_list, retry_index
            )
            if revived is not None:
                notify_recovered(slack_config, hostname, revived)

            value_map, is_success, newly_failed, newly_recovered = my_lib.sensor.sense(
                active_sensor_list, FAIL_THRESHOLD
            )
            value_map.update({"hostname": hostname})

            for failed in newly_failed:
                notify_failed(slack_config, hostname, failed)
                # NOTE: 連続失敗したセンサーは inactive に降格し、retry_inactive の
                # ラウンドロビンで復帰を試みる。壊れたセンサー 1 台が liveness を
                # 止め続けて再起動フラップになるのを防ぐ。
                active_sensor_list.remove(failed.sensor)
                inactive_sensor_list.append(failed.sensor)

            for sensor in newly_recovered:
                notify_recovered(slack_config, hostname, sensor)

            elapsed_time = time.time() - time_start

            if once:
                logging.info("計測結果 (dry-run): %s", value_map)
                break

            data_preserved = my_lib.fluentd_util.send(sender, fluentd_label, value_map)
            if data_preserved:
                logging.info("Send OK.")
                if spool is not None:
                    spool.replay(
                        lambda label, data, timestamp: my_lib.fluentd_util.send_with_time(
                            sender, label, data, timestamp
                        )
                    )
            elif spool is not None:
                # NOTE: fluentd 断でもデータを失わないようにディスクへ退避する
                data_preserved = spool.append(fluentd_label, value_map, time.time())

            my_lib.fluentd_util.send(
                sender,
                "meta",
                build_meta(
                    hostname,
                    elapsed_time,
                    is_success,
                    active_sensor_list,
                    inactive_sensor_list,
                    spool.count() if spool is not None else 0,
                ),
            )

            if is_success and data_preserved:
                # NOTE: センシングが成功し、かつデータが保全されている (送信済み or
                # スプール済み) 場合のみ Liveness を更新する
                my_lib.footprint.update(pathlib.Path(config["liveness"]["file"]["sensing"]))

            sleep_time = max(interval_sec - (time.time() - time_start), 1)

            if should_terminate.is_set():
                logging.warning("Terminate signal received")
                break

            logging.info("Sleep %.1f sec...", sleep_time)
            # NOTE: シグナル受信で即座に抜ける (time.sleep だと PEP 475 で再開してしまう)
            if should_terminate.wait(sleep_time):
                logging.warning("Terminate signal received")
                break
    finally:
        my_lib.sensor.close(sensor_list)
        if sender is not None:
            # NOTE: 内部バッファの未送信データを flush してから終了する
            my_lib.fluentd_util.close(sender)


def show_sensor_list(config: dict[str, Any]) -> int:
    """設定された全センサーを ping して一覧表示する。全て応答すれば 0 を返す。"""
    sensor_list = my_lib.sensor.load(config["sensor"])

    result = []
    for sensor in sensor_list:
        alive = sensor.ping()
        result.append((my_lib.sensor.sensor_info(sensor), "OK" if alive else "NG"))

    width = max(len(info) for info, _ in result) if result else 0
    print(f"{'SENSOR':<{width}}  STATUS")  # noqa: T201
    for info, status in result:
        print(f"{info:<{width}}  {status}")  # noqa: T201

    my_lib.sensor.close(sensor_list)

    return 0 if all(status == "OK" for _, status in result) else 1


def main() -> None:
    args = docopt.docopt(__doc__)

    config_file = args["-c"]
    debug_mode = args["-D"]

    my_lib.logger.init("sensing", level=logging.DEBUG if debug_mode else logging.INFO)

    config = my_lib.config.load(config_file, sensing.get_schema_path())

    if args["--check-config"]:
        # NOTE: ここまで来た時点でスキーマ検証は通っている。ドライバ名も検証する。
        for sensor_def in config["sensor"]:
            my_lib.sensor.resolve_driver(sensor_def["name"])
        logging.info("設定ファイルに問題はありません: %s", config_file)
        sys.exit(0)

    if args["--list"]:
        sys.exit(show_sensor_list(config))

    execute(config, once=args["--once"])


if __name__ == "__main__":
    main()
