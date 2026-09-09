"""D1 direction-only correction; D0 detector and ownership remain unchanged."""
from __future__ import annotations
import copy
import math
from .models import stable_id
from .structure_v04 import ExclusiveLedger, ScaleGrammar, TimeStructureEngine

SCHEMA='two_wave_same_scale_direction@0.4.1'


def audit_d0_direction(record: dict, config: ScaleGrammar | None=None) -> dict:
    c=config or ScaleGrammar()
    if record['operator']!='D0' or record['grammar_hash']!=c.config_hash:
        raise ValueError('D1 requires matching unmodified D0 grammar')
    r=copy.deepcopy(record);steps=r.get('phase_steps');spans=r.get('phase_spans')
    reason='direction_unchanged'
    finite=(isinstance(steps,list) and len(steps)==3 and all(math.isfinite(v) for v in steps)
            and isinstance(spans,list) and len(spans)==2 and all(math.isfinite(v) for v in spans))
    if not finite:
        label='uncertain';reason='undefined_phase_geometry'
    elif min(steps)>c.phase_step:
        label='uptrend';reason='all_three_phases_clear_up'
    elif max(steps)<-c.phase_step:
        label='downtrend';reason='all_three_phases_clear_down'
    elif record['direction'] in ('uptrend','downtrend'):
        label=record['direction'];reason='retain_strong_drift_with_nonopposed_weak_phase'
    elif max(abs(v) for v in steps)<=c.phase_step and max(spans)<=c.drift:
        label='range';reason='all_three_phases_small'
    else:
        label='uncertain';reason='net_drift_alone_does_not_establish_range'
    r.update(schema_version=SCHEMA,operator='D1',detector_operator='D0',
        source_D0_record_id=record['record_id'],source_D0_direction=record['direction'],
        direction=label,direction_reasons=[] if label!='uncertain' else [reason],
        direction_audit_reason=reason,direction_changed=label!=record['direction'])
    r['record_id']=stable_id('D1_pair',[SCHEMA,c.config_hash,record['record_id']])
    return r


class TimeDirectionEngine:
    """Online D1 adapter, not a second detector or an ownership re-optimizer."""
    def __init__(self,timeframe: str='5m_offset_0',config: ScaleGrammar | None=None):
        self.source=TimeStructureEngine(timeframe,config)
        self.ledger=ExclusiveLedger()

    @property
    def records(self):
        return self.ledger.candidates

    def update(self,bar: dict) -> list[dict]:
        out=[]
        for original in self.source.update(bar):
            revised=self.ledger.offer(audit_d0_direction(original,self.source.config))
            assert revised['selected']==original['selected']
            out.append(revised)
        return out
