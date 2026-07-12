#!/usr/bin/env python3
"""Fluentd 送信失敗時にレコードをディスクへ退避し、復旧後に再送するためのスプール。

fluent-logger の内部バッファは最大 1MB (超過分は破棄) かつプロセス終了で消えるため、
長時間のネットワーク断でもデータを失わないように JSON Lines 形式でファイルに退避する。
"""

from __future__ import annotations

import json
import logging
import pathlib
from collections.abc import Callable
from typing import Any

# 1 回の replay で再送する最大レコード数 (復旧直後にループを長時間占有しないための上限)
REPLAY_LIMIT: int = 500


class Spool:
    def __init__(self, path: pathlib.Path, max_mb: float = 10.0) -> None:
        self.path = path
        self.max_bytes = int(max_mb * 1024 * 1024)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def append(self, label: str, data: dict[str, Any], timestamp: float) -> bool:
        """レコードを退避する。成功時 True。上限超過や書き込み失敗時は False。"""
        try:
            record = json.dumps(
                {"time": timestamp, "label": label, "data": data}, ensure_ascii=False
            )
            if self.path.exists() and (self.path.stat().st_size + len(record)) > self.max_bytes:
                logging.warning(
                    "スプールが上限 (%d MB) に達したため、レコードを破棄します",
                    self.max_bytes // (1024 * 1024),
                )
                return False

            with self.path.open("a", encoding="utf-8") as f:
                f.write(record + "\n")
            return True
        except (OSError, TypeError, ValueError):
            logging.exception("スプールへの書き込みに失敗")
            return False

    def replay(self, send_func: Callable[[str, dict[str, Any], float], bool]) -> int:
        """スプールから再送する。

        send_func(label, data, timestamp) が True を返したレコードは削除する。
        送信に失敗したら (fluentd がまだ不調とみなして) 以降のレコードは持ち越す。
        再送できた件数を返す。
        """
        if not self.path.exists():
            return 0

        try:
            lines = [line for line in self.path.read_text(encoding="utf-8").splitlines() if line]
        except OSError:
            logging.exception("スプールの読み込みに失敗")
            return 0

        if not lines:
            return 0

        sent = 0
        remain: list[str] = []
        for i, line in enumerate(lines):
            if sent >= REPLAY_LIMIT:
                remain = lines[i:]
                break

            try:
                record = json.loads(line)
                label = record["label"]
                data = record["data"]
                timestamp = float(record["time"])
            except (json.JSONDecodeError, KeyError, TypeError, ValueError):
                logging.warning("壊れたスプールレコードを破棄: %.100s", line)
                continue

            if send_func(label, data, timestamp):
                sent += 1
            else:
                remain = lines[i:]
                break

        try:
            if remain:
                self.path.write_text("\n".join(remain) + "\n", encoding="utf-8")
            else:
                self.path.unlink(missing_ok=True)
        except OSError:
            logging.exception("スプールの更新に失敗")

        if sent:
            logging.info("スプールから %d 件を再送しました (残り %d 件)", sent, len(remain))

        return sent

    def count(self) -> int:
        """スプール内のレコード数を返す。"""
        if not self.path.exists():
            return 0
        try:
            return sum(1 for line in self.path.read_text(encoding="utf-8").splitlines() if line)
        except OSError:
            return 0
