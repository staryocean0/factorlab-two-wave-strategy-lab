"""Mechanism tests for the range-audit revision; no human accuracy claims."""
import copy
import importlib.util
from pathlib import Path

import pytest

from factor_lab.visual_structure.two_wave.frequency_v03 import DirectionEngine as C0
from factor_lab.visual_structure.two_wave.frequency_v031 import DirectionEngine, audit_range_record

spec = importlib.util.spec_from_file_location("v03_test_helpers", Path(__file__).with_name("test_two_wave_frequency_v03.py"))
helpers = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helpers)


def make(steps, label="range"):
    return {"direction_classification": label, "direction_record_id": "test", "config_hash": "c0",
            "source_structure_id": "s", "phase_displacements_in_widths": steps,
            "direction_rejection_reasons": [], "trade_authority": False}


@pytest.mark.parametrize("steps", [[.4594,-.1715,-.4462], [.2,.1,-.25]])
def test_opposed_migration_not_flat_range(steps):
    r=make(steps);before=copy.deepcopy(r);out=audit_range_record(r)
    assert out["direction_classification"]=="uncertain"
    assert out["range_audit_conflicts"] and r==before
    assert out["direction_record_id"]!=r["direction_record_id"]


def test_small_fluctuations_and_trends_unchanged():
    assert audit_range_record(make([.1,-.05,-.1]))["direction_classification"]=="range"
    assert audit_range_record(make([.3,.8,.5],"uptrend"))["direction_classification"]=="uptrend"


def test_all_prefixes_and_source_stream_unchanged():
    bars=helpers.stream();e=DirectionEngine();base=C0();emitted=[]
    for row in bars:emitted.extend(e.update(row));base.update(row)
    assert emitted==e.records and e.source.export()==base.source.export()
    assert e.records==[audit_range_record(r) for r in base.records]
    emitted[0]["D"]=123
    assert e.records[0]["D"]!=123
    for n in range(1,len(bars)+1):
        prefix=DirectionEngine()
        for row in bars[:n]:prefix.update(row)
        assert prefix.records==[r for r in e.records if r["confirmation_bar"]<n]


def test_invalid_range_input_fails_closed():
    with pytest.raises(ValueError):audit_range_record(make([.1,float('nan'),.2]))
    with pytest.raises(ValueError):audit_range_record(make([.1,.1,.1]),0)
