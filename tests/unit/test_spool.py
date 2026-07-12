#!/usr/bin/env python3
"""Fluentd スプール (F-6) のテスト。"""

from __future__ import annotations

import json

import sensing.spool


def test_append_and_count(tmp_path):
    spool = sensing.spool.Spool(tmp_path / "spool.jsonl")

    assert spool.count() == 0
    assert spool.append("rasp", {"temp": 25.0}, 1000.0)
    assert spool.append("rasp", {"temp": 26.0}, 1020.0)
    assert spool.count() == 2


def test_replay_all_success(tmp_path):
    spool = sensing.spool.Spool(tmp_path / "spool.jsonl")
    spool.append("rasp", {"temp": 25.0}, 1000.0)
    spool.append("rasp", {"temp": 26.0}, 1020.0)

    sent = []
    count = spool.replay(lambda label, data, ts: sent.append((label, data, ts)) or True)

    assert count == 2
    assert sent[0] == ("rasp", {"temp": 25.0}, 1000.0)
    assert spool.count() == 0
    assert not spool.path.exists()


def test_replay_partial_failure_keeps_remainder(tmp_path):
    """再送に失敗したレコード以降は持ち越されること。"""
    spool = sensing.spool.Spool(tmp_path / "spool.jsonl")
    for i in range(3):
        spool.append("rasp", {"index": i}, 1000.0 + i)

    results = iter([True, False])
    count = spool.replay(lambda label, data, ts: next(results, False))

    assert count == 1
    assert spool.count() == 2


def test_replay_drops_corrupted_line(tmp_path):
    spool = sensing.spool.Spool(tmp_path / "spool.jsonl")
    spool.append("rasp", {"temp": 25.0}, 1000.0)

    with spool.path.open("a") as f:
        f.write("THIS IS NOT JSON\n")

    spool.append("rasp", {"temp": 26.0}, 1020.0)

    count = spool.replay(lambda label, data, ts: True)

    assert count == 2
    assert not spool.path.exists()


def test_append_respects_max_size(tmp_path):
    spool = sensing.spool.Spool(tmp_path / "spool.jsonl", max_mb=0.0001)  # 約 100 bytes

    assert spool.append("rasp", {"temp": 25.0}, 1000.0)
    assert not spool.append("rasp", {"temp": 26.0, "padding": "x" * 200}, 1020.0)
    assert spool.count() == 1


def test_record_format(tmp_path):
    spool = sensing.spool.Spool(tmp_path / "spool.jsonl")
    spool.append("rasp", {"temp": 25.0}, 1000.0)

    record = json.loads(spool.path.read_text().strip())
    assert record == {"time": 1000.0, "label": "rasp", "data": {"temp": 25.0}}
