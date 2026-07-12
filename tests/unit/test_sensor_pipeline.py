#!/usr/bin/env python3
"""my_lib.sensor の ping / retry_inactive / sense の契約を検証する。"""

from __future__ import annotations

import my_lib.sensor
import pytest


class TestPing:
    def test_partition(self, make_sensor):
        alive = make_sensor(name="ALIVE")
        dead = make_sensor(name="DEAD", ping_result=False)

        active, inactive = my_lib.sensor.ping([alive, dead])

        assert active == [alive]
        assert inactive == [dead]

    def test_raising_ping_does_not_crash(self, make_sensor):
        """ping が例外を投げるセンサーがいてもアプリ全体は落ちない (P0-4)。"""
        broken = make_sensor(name="BROKEN", ping_result=UnicodeDecodeError("utf-8", b"", 0, 1, "x"))

        active, inactive = my_lib.sensor.ping([broken])

        assert active == []
        assert inactive == [broken]

    def test_required_sensor_missing_raises(self, make_sensor):
        dead = make_sensor(name="DEAD", ping_result=False)
        dead.required = True

        with pytest.raises(RuntimeError):
            my_lib.sensor.ping([dead])


class TestRetryInactive:
    def test_revive(self, make_sensor):
        revived = make_sensor(name="REVIVED")
        active, inactive = [], [revived]

        index, sensor = my_lib.sensor.retry_inactive(active, inactive, 0)

        assert sensor is revived
        assert active == [revived]
        assert inactive == []
        assert index == 0

    def test_no_revive_advances_index(self, make_sensor):
        dead = make_sensor(name="DEAD", ping_result=False)
        active, inactive = [], [dead]

        index, sensor = my_lib.sensor.retry_inactive(active, inactive, 0)

        assert sensor is None
        assert inactive == [dead]
        assert index == 1

    def test_empty_inactive(self):
        assert my_lib.sensor.retry_inactive([], [], 5) == (0, None)


class TestSense:
    def test_success(self, make_sensor):
        sensor = make_sensor(name="S1", value_map={"temp": 25.0})

        value_map, is_success, newly_failed, newly_recovered = my_lib.sensor.sense([sensor])

        assert value_map == {"temp": 25.0}
        assert is_success
        assert newly_failed == []
        assert newly_recovered == []

    def test_newly_failed_only_at_threshold(self, make_sensor):
        """連続失敗がちょうど閾値に達した 1 回だけ通知対象になること。"""
        sensor = make_sensor(name="S1")
        sensor.fail_exception = RuntimeError("boom")

        _, is_success, newly_failed, _ = my_lib.sensor.sense([sensor], fail_threshold=2)
        assert not is_success
        assert newly_failed == []

        _, _, newly_failed, _ = my_lib.sensor.sense([sensor], fail_threshold=2)
        assert len(newly_failed) == 1
        assert newly_failed[0].sensor is sensor
        assert "boom" in newly_failed[0].traceback

        _, _, newly_failed, _ = my_lib.sensor.sense([sensor], fail_threshold=2)
        assert newly_failed == []

    def test_newly_recovered(self, make_sensor):
        """閾値以上失敗していたセンサーが成功に転じたら newly_recovered に入ること。"""
        sensor = make_sensor(name="S1", value_map={"temp": 25.0})
        sensor.fail_exception = RuntimeError("boom")

        my_lib.sensor.sense([sensor], fail_threshold=2)
        my_lib.sensor.sense([sensor], fail_threshold=2)

        sensor.fail_exception = None
        _, _, _, newly_recovered = my_lib.sensor.sense([sensor], fail_threshold=2)

        assert newly_recovered == [sensor]
        assert sensor.consecutive_fails == 0

    def test_key_collision_warns(self, make_sensor, caplog):
        """同一キーの silent overwrite を warning で検出できること (P2-1)。"""
        sensor_a = make_sensor(name="A", value_map={"lux": 100})
        sensor_b = make_sensor(name="B", value_map={"lux": 200})

        value_map, _, _, _ = my_lib.sensor.sense([sensor_a, sensor_b])

        assert value_map["lux"] == 200
        assert any("重複" in record.message for record in caplog.records)

    def test_field_prefix_and_rename(self, make_sensor):
        """field_prefix / rename でキー衝突を回避できること (F-3)。"""
        sensor_a = make_sensor(name="A", value_map={"lux": 100})
        sensor_b = make_sensor(name="B", value_map={"lux": 200, "temp": 20})
        sensor_b.field_prefix = "outdoor_"
        sensor_b.field_rename = {"temp": "air_temp"}

        value_map, _, _, _ = my_lib.sensor.sense([sensor_a, sensor_b])

        assert value_map == {"lux": 100, "outdoor_lux": 200, "outdoor_air_temp": 20}


class TestClose:
    def test_close_all(self, make_sensor):
        sensor_list = [make_sensor(name="A"), make_sensor(name="B")]

        my_lib.sensor.close(sensor_list)

        assert all(sensor.closed for sensor in sensor_list)
