#!/usr/bin/env python3
"""sensing.cli.app のメインループのテスト。"""

from __future__ import annotations

import my_lib.fluentd_util
import my_lib.footprint
import my_lib.sensor
import pytest

import sensing.cli.app
import sensing.spool


@pytest.fixture
def base_config(tmp_path):
    return {
        "base_dir": tmp_path,
        "fluentd": {
            "host": "localhost",
            "spool_file": str(tmp_path / "spool.jsonl"),
        },
        "sensor": [{"name": "fake"}],
        "sensing": {"interval_sec": 1},
        "liveness": {"file": {"sensing": str(tmp_path / "healthz")}},
    }


@pytest.fixture
def fake_pipeline(monkeypatch, make_sensor):
    """my_lib.sensor.load とfluentd をフェイクに差し替える。"""
    sensor = make_sensor(name="FAKE", value_map={"temp": 25.0})
    monkeypatch.setattr(my_lib.sensor, "load", lambda sensor_def_list: [sensor])

    sent: list[tuple[str, dict]] = []
    state = {"send_ok": True}

    monkeypatch.setattr(my_lib.fluentd_util, "get_handle", lambda *args, **kwargs: object())
    monkeypatch.setattr(
        my_lib.fluentd_util,
        "send",
        lambda handle, label, data: (sent.append((label, dict(data))) or True)
        if state["send_ok"]
        else False,
    )
    monkeypatch.setattr(
        my_lib.fluentd_util,
        "send_with_time",
        lambda handle, label, data, ts: state["send_ok"] and (sent.append((label, dict(data))) or True),
    )
    monkeypatch.setattr(my_lib.fluentd_util, "close", lambda handle: None)

    return {"sensor": sensor, "sent": sent, "state": state}


def run_one_cycle(config):
    """1 周期実行して終了させる。"""
    sensing.cli.app.should_terminate.set()
    try:
        sensing.cli.app.execute(config)
    finally:
        sensing.cli.app.should_terminate.clear()


def test_once_mode_does_not_send_or_update_liveness(base_config, fake_pipeline, tmp_path):
    sensing.cli.app.execute(base_config, once=True)

    assert fake_pipeline["sent"] == []
    assert not (tmp_path / "healthz").exists()


def test_normal_cycle_sends_and_updates_liveness(base_config, fake_pipeline):
    run_one_cycle(base_config)

    labels = [label for label, _ in fake_pipeline["sent"]]
    assert "rasp" in labels
    assert "meta" in labels

    data = dict(fake_pipeline["sent"][labels.index("rasp")][1])
    assert data["temp"] == 25.0
    assert "hostname" in data

    assert my_lib.footprint.exists(base_config["liveness"]["file"]["sensing"])


def test_send_failure_spools_and_updates_liveness(base_config, fake_pipeline, tmp_path):
    """送信失敗時はスプールに退避され、liveness は更新されること (P2-11, F-6)。"""
    fake_pipeline["state"]["send_ok"] = False

    run_one_cycle(base_config)

    spool = sensing.spool.Spool(tmp_path / "spool.jsonl")
    assert spool.count() == 1
    assert my_lib.footprint.exists(base_config["liveness"]["file"]["sensing"])

    # NOTE: 復旧後の周回でスプールが再送されること
    fake_pipeline["state"]["send_ok"] = True
    run_one_cycle(base_config)
    assert spool.count() == 0


def test_send_failure_without_spool_blocks_liveness(base_config, fake_pipeline):
    """スプール未設定で送信失敗した場合は liveness を更新しないこと。"""
    del base_config["fluentd"]["spool_file"]
    fake_pipeline["state"]["send_ok"] = False

    run_one_cycle(base_config)

    assert not my_lib.footprint.exists(base_config["liveness"]["file"]["sensing"])


def test_sensor_failure_blocks_liveness_and_demotes(base_config, fake_pipeline, monkeypatch):
    """計測失敗時は liveness を更新せず、閾値到達でセンサーが inactive に降格すること。"""
    fake_pipeline["sensor"].fail_exception = RuntimeError("boom")

    notified = []
    monkeypatch.setattr(
        sensing.cli.app, "notify_failed", lambda slack_config, hostname, failed: notified.append(failed)
    )

    run_one_cycle(base_config)
    assert not my_lib.footprint.exists(base_config["liveness"]["file"]["sensing"])
    assert notified == []

    run_one_cycle(base_config)
    assert len(notified) == 1
    assert notified[0].sensor is fake_pipeline["sensor"]
