#!/usr/bin/env python3
"""my_lib.sensor.load() が config 定義からドライバを構築できることを検証する。"""

from __future__ import annotations

import pathlib

import my_lib.sensor
import pytest


def test_load_i2c_default_bus(fake_bus):
    sensor_list = my_lib.sensor.load([{"name": "sht35"}])

    assert len(sensor_list) == 1
    assert sensor_list[0].NAME == "SHT-35"
    assert sensor_list[0].required is False


def test_load_all_example_sensors(fake_bus, repo_root):
    """example config の全センサーが構築できること (P0-1 の回帰テスト)。"""
    import my_lib.config

    import sensing

    config = my_lib.config.load(repo_root / "config.example.yaml", sensing.get_schema_path())

    # NOTE: i2c_bus 指定のセンサーはテスト環境にバスがないためスキップされる
    loadable = [s for s in config["sensor"] if "i2c_bus" not in s]
    sensor_list = my_lib.sensor.load(loadable)

    assert len(sensor_list) == len(loadable)


def test_load_unknown_name():
    with pytest.raises(ValueError, match="未知のセンサー名"):
        my_lib.sensor.load([{"name": "nonexistent"}])


def test_load_missing_i2c_bus_skips(fake_bus):
    """存在しない I2C バスのセンサーは warning でスキップされること。"""
    if pathlib.Path("/dev/i2c-0").exists():
        pytest.skip("/dev/i2c-0 が存在する環境ではスキップ動作を検証できない")

    sensor_list = my_lib.sensor.load([{"name": "veml6075", "i2c_bus": "VC"}])

    assert sensor_list == []


def test_load_lowercase_i2c_bus(fake_bus):
    """小文字の i2c_bus 指定 (vc) も解釈されること (P0-2)。"""
    if pathlib.Path("/dev/i2c-0").exists():
        pytest.skip("/dev/i2c-0 が存在する環境ではスキップ動作を検証できない")

    # NOTE: バス名は解決される (未知バス名なら ValueError になる)
    sensor_list = my_lib.sensor.load([{"name": "veml6075", "i2c_bus": "vc"}])
    assert sensor_list == []

    with pytest.raises(ValueError, match="未知の I2C バス名"):
        my_lib.sensor.load([{"name": "veml6075", "i2c_bus": "bogus"}])


def test_load_missing_uart_dev_skips(fake_bus):
    """存在しない UART デバイスのセンサーは warning でスキップされること (P2-7)。"""
    sensor_list = my_lib.sensor.load([{"name": "rg_15", "uart_dev": "/dev/ttyNOEXIST"}])

    assert sensor_list == []


def test_load_field_naming_options(fake_bus):
    sensor_list = my_lib.sensor.load(
        [{"name": "sht35", "field_prefix": "room_", "rename": {"temp": "air_temp"}}]
    )

    assert sensor_list[0].field_prefix == "room_"
    assert sensor_list[0].field_rename == {"temp": "air_temp"}


def test_load_max31856(fake_bus):
    """SPI センサー (MAX31856) が load() 経由で構築できること (P0-1)。"""
    sensor_list = my_lib.sensor.load([{"name": "max31856"}])

    assert sensor_list[0].NAME == "MAX31856"
    assert sensor_list[0].TYPE == "SPI"
