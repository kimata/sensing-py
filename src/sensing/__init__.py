"""I2C/SPI/UART で接続されたセンサーで計測を行い、結果を Fluentd で送信するアプリです。"""

from __future__ import annotations

import importlib.resources
import pathlib


def get_schema_path() -> pathlib.Path:
    """パッケージ内の config.schema のパスを返す (CWD 非依存)。"""
    return pathlib.Path(str(importlib.resources.files("sensing").joinpath("config.schema")))
