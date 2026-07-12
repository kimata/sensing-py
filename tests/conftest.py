#!/usr/bin/env python3
"""共有フィクスチャ。

実ハードウェア (I2C/SPI/UART) なしでテストできるように、
smbus2 / spidev をフェイクに差し替える。
"""

from __future__ import annotations

import pathlib

import my_lib.sensor
import pytest


class FakeSMBus:
    """smbus2.SMBus のフェイク。全レジスタ 0 を返す。"""

    def __init__(self, bus_id):
        self.bus_id = bus_id
        self.closed = False

    def write_byte_data(self, dev_addr, register, data):
        pass

    def read_byte_data(self, dev_addr, register):
        return 0

    def read_i2c_block_data(self, dev_addr, register, length):
        return [0] * length

    def i2c_rdwr(self, *i2c_msgs):
        pass

    def close(self):
        self.closed = True


class FakeSpiDev:
    """spidev.SpiDev のフェイク。"""

    def __init__(self):
        self.max_speed_hz = 0
        self.mode = 0
        self.closed = False

    def open(self, bus, dev):
        pass

    def xfer2(self, data):
        return [0] * len(data)

    def close(self):
        self.closed = True


@pytest.fixture
def fake_bus(monkeypatch):
    """I2C/SPI をフェイクに差し替える。"""
    import smbus2
    import spidev

    monkeypatch.setattr(smbus2, "SMBus", FakeSMBus)
    monkeypatch.setattr(spidev, "SpiDev", FakeSpiDev)


class FakeSensor(my_lib.sensor.SensorBase):
    """テスト用のフェイクセンサー。"""

    TYPE = "I2C"

    def __init__(self, name="FAKE", value_map=None, ping_result=True, dev_addr=0x10):
        super().__init__()
        self.NAME = name
        self.dev_addr = dev_addr
        self.value_map = value_map if value_map is not None else {"value": 1.0}
        self.ping_result = ping_result
        self.fail_exception: Exception | None = None
        self.closed = False

    def ping(self):
        if isinstance(self.ping_result, Exception):
            raise self.ping_result
        return self.ping_result

    def get_value_map(self):
        if self.fail_exception is not None:
            raise self.fail_exception
        return dict(self.value_map)

    def close(self):
        self.closed = True


@pytest.fixture
def make_sensor():
    return FakeSensor


@pytest.fixture
def repo_root():
    return pathlib.Path(__file__).parent.parent
