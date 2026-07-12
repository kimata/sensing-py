#!/usr/bin/env python3
"""config.example.yaml・config.schema・my_lib.sensor.load() の契約が一致していることを検証する。

このテストが存在していれば、「example 設定に存在しないドライバ名が載っている」
「schema にあるキーを load() が読まない」といった不整合 (P0-1, P0-2) を防げる。
"""

from __future__ import annotations

import my_lib.config
import my_lib.sensor
import pytest
import yaml

import sensing


def load_example_config(repo_root):
    return my_lib.config.load(repo_root / "config.example.yaml", sensing.get_schema_path())


def test_example_config_is_valid(repo_root):
    config = load_example_config(repo_root)

    assert config["fluentd"]["host"]
    assert config["sensing"]["interval_sec"] >= 1


def test_example_config_sensor_names_resolve(repo_root):
    """example 設定の全センサー名が実在するドライバに解決できること。"""
    config = load_example_config(repo_root)

    for sensor_def in config["sensor"]:
        driver = my_lib.sensor.resolve_driver(sensor_def["name"])
        assert issubclass(driver, my_lib.sensor.SensorBase)


def test_unknown_driver_name_raises_with_suggestion():
    with pytest.raises(ValueError, match="veml7700"):
        my_lib.sensor.resolve_driver("veml770")


def test_non_sensor_class_is_rejected():
    """bp35a1 (通信モジュール) や echonetlite (プロトコル) は指定できないこと。"""
    with pytest.raises(ValueError, match="未知のセンサー名"):
        my_lib.sensor.resolve_driver("bp35a1")

    with pytest.raises(ValueError, match="未知のセンサー名"):
        my_lib.sensor.resolve_driver("echonetlite")


def test_schema_rejects_unknown_sensor_key(repo_root, tmp_path):
    """かつての「bus: vc が黙って無視される」事故 (P0-2) を防ぐ。"""
    config = yaml.safe_load((repo_root / "config.example.yaml").read_text())
    config["sensor"][0]["bus"] = "vc"

    config_path = tmp_path / "config.yaml"
    config_path.write_text(yaml.safe_dump(config, allow_unicode=True))

    with pytest.raises(my_lib.config.ConfigValidationError):
        my_lib.config.load(config_path, sensing.get_schema_path())


def test_schema_accepts_i2c_bus(repo_root, tmp_path):
    config = yaml.safe_load((repo_root / "config.example.yaml").read_text())
    config["sensor"][0]["i2c_bus"] = "VC"

    config_path = tmp_path / "config.yaml"
    config_path.write_text(yaml.safe_dump(config, allow_unicode=True))

    loaded = my_lib.config.load(config_path, sensing.get_schema_path())
    assert loaded["sensor"][0]["i2c_bus"] == "VC"


def test_schema_path_is_cwd_independent(repo_root, tmp_path, monkeypatch):
    """CWD がどこでも schema が解決できること (P1-6)。"""
    monkeypatch.chdir(tmp_path)
    config = load_example_config(repo_root)
    assert "sensor" in config
