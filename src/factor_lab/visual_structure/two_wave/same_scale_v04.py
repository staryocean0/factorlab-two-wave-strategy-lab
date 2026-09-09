"""Time-constrained raw-price two-cycle research. No trade or current-state output.

Implements frozen v0.4 / v0.4.1 with v0.4.2 clock/price clarifications.
C1 remains untouched; C2G is only its geometry qualification control.
"""
from __future__ import annotations

import copy
import math
from dataclasses import asdict, dataclass
from datetime import datetime
from zoneinfo import ZoneInfo

import numpy as np

from .engine import Engine
from .geometry import fit_geometry
from .models import Config, stable_id

SCHEMA = 'two_wave_same_scale@0.4.2'


@dataclass(frozen=True)
class ScaleConfig:
    timeframe: str = '5m_offset_0'
    reversal_bars: int = 3
    max_unfinished_leg: int = 48
    min_leg: int = 4
    min_cycle: int = 12
    max_cycle: int = 48
    max_pair: int = 96
    duration_ratio: float = 2.0
    amplitude_ratio: float = 2.0
    min_leg_efficiency: float = .5
    max_jump_share: float = .5
    max_flat_share: float = .5
    max_observed_days: int = 3
    max_wall_days: float = 7.0
    max_confirmation_delay: int = 8
    phase_tolerance: float = .15
    opposite_tolerance: float = .05
    strong_drift: float = .5

    def __post_init__(self):
        if not isinstance(self.timeframe, str) or not self.timeframe:
            raise ValueError('nonempty timeframe required')
        integer_fields = ('reversal_bars', 'max_unfinished_leg', 'min_leg', 'min_cycle',
                          'max_cycle', 'max_pair', 'max_observed_days', 'max_confirmation_delay')
        for key, value in asdict(self).items():
            if key == 'timeframe':
                continue
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0:
                raise ValueError(f'{key} must be finite positive')
            if key in integer_fields and not isinstance(value, int):
                raise ValueError(f'{key} must be an integer')
        if self.min_cycle > self.max_cycle or self.min_cycle < 2 * self.min_leg:
            raise ValueError('inconsistent leg/cycle durations')
        if min(self.duration_ratio, self.amplitude_ratio) < 1 or self.max_pair < 2 * self.min_cycle:
            raise ValueError('invalid scale ratios/pair limit')
        if any(getattr(self, k) > 1 for k in ('min_leg_efficiency', 'max_jump_share', 'max_flat_share')):
            raise ValueError('path proportions must be <=1')
        if self.opposite_tolerance > self.phase_tolerance:
            raise ValueError('opposite tolerance must not exceed phase tolerance')

    @property
    def config_hash(self):
        return stable_id('same_scale_cfg', {'schema': SCHEMA, **asdict(self)})


def _ratio(values):
    return max(values) / min(values) if min(values) > 0 else None


def direction_versions(steps, spans, cfg):
    """Return D0 and D1; neither has access to future returns or channel quality."""
    if len(steps) != 3 or len(spans) != 2 or not all(math.isfinite(x) for x in [*steps, *spans]):
        raise ValueError('three finite phase steps and two spans required')
    drift = steps[0] + steps[1]
    sign = 1 if drift > 0 else -1
    directed = [sign * x for x in steps]
    strong = abs(drift) > cfg.strong_drift and sum(x > cfg.phase_tolerance for x in directed) >= 2
    strong = strong and min(directed) >= -cfg.opposite_tolerance
    opposed = min(steps) < -cfg.phase_tolerance and max(steps) > cfg.phase_tolerance
    d0 = ('uptrend' if sign > 0 else 'downtrend') if strong else (
        'range' if max(spans) <= cfg.strong_drift and not opposed else 'uncertain')
    if min(steps) > cfg.phase_tolerance:
        d1, reason = 'uptrend', 'all_three_phases_up'
    elif max(steps) < -cfg.phase_tolerance:
        d1, reason = 'downtrend', 'all_three_phases_down'
    elif strong:
        d1, reason = ('uptrend' if sign > 0 else 'downtrend'), 'strong_drift_two_phases_no_opposition'
    elif max(abs(x) for x in steps) <= cfg.phase_tolerance and max(spans) <= cfg.strong_drift:
        d1, reason = 'range', 'all_phase_migrations_small'
    else:
        d1, reason = 'uncertain', 'phase_migration_or_conflict_not_resolved'
    return {'D0': d0, 'D1': d1, 'D1_reason': reason, 'changed_from_D0': d0 != d1}


def evaluate_pair(points, bars, cfg, *, source='D1', source_record=None):
    """Audit five exact confirmed extrema; all qualification failures are retained."""
    if len(points) != 5 or any(p.get('left_censored', False) for p in points):
        raise ValueError('five uncensored confirmed pivots required')
    ids = [p['occurrence_bar'] for p in points]
    if any(isinstance(i, bool) or not isinstance(i, int) for i in ids) or ids[0] < 0 or ids[-1] >= len(bars):
        raise ValueError('integer pivot positions within supplied bars required')
    if any(p['kind'] not in ('high', 'low') or p['confirmation_bar'] < p['occurrence_bar'] for p in points):
        raise ValueError('real pivot kinds and valid occurrence/confirmation order required')
    if any(not math.isfinite(p['price']) or p['price'] != bars[i]['close'] for p, i in zip(points, ids)):
        raise ValueError('pivot prices must match observed closes')
    if any((b['price']-a['price'])*(1 if a['kind']=='low' else -1) <= 0 for a, b in zip(points, points[1:])):
        raise ValueError('actual alternating price turns required')
    if any(a >= b for a, b in zip(ids, ids[1:])) or any(a['kind'] == b['kind'] for a, b in zip(points, points[1:])):
        raise ValueError('ordered alternating pivots required')
    confirm = points[-1]['confirmation_bar']
    if confirm >= len(bars) or ids[-1] > confirm or any(p['confirmation_bar'] > confirm for p in points):
        raise ValueError('no future or unconfirmed pivot may be used')
    x = [p['price'] for p in points]
    legs = [b - a for a, b in zip(ids, ids[1:])]
    cycles = [ids[2] - ids[0], ids[4] - ids[2]]
    amplitudes = [abs(x[k+1] - (x[k] + (x[k+2]-x[k]) * legs[k] / cycles[k//2])) for k in (0, 2)]
    unit = sum(amplitudes) / 2
    paths = []
    for a, b in zip(ids, ids[1:]):
        y = np.asarray([v['close'] for v in bars[a:b+1]], float)
        changes = np.abs(np.diff(y)); length = float(changes.sum())
        paths.append({'efficiency': abs(float(y[-1]-y[0])) / length if length else 0.0,
                      'jump_share': float(changes.max()) / length if length else 1.0,
                      'flat_share': float(np.mean(changes == 0))})
    days = {v.get('trading_day') or datetime.fromisoformat(v['timestamp']).astimezone(ZoneInfo('Asia/Shanghai')).date().isoformat()
            for v in bars[ids[0]:ids[-1]+1]}
    wall_days = (datetime.fromisoformat(bars[ids[-1]]['timestamp']) - datetime.fromisoformat(bars[ids[0]]['timestamp'])).total_seconds()/86400
    duration_ratios = [_ratio(cycles), _ratio(legs[::2]), _ratio(legs[1::2])]
    amplitude_ratio = _ratio(amplitudes)
    delay = confirm - ids[-1]
    reasons = []
    checks = {'short_leg': min(legs) < cfg.min_leg, 'short_cycle': min(cycles) < cfg.min_cycle,
              'long_cycle': max(cycles) > cfg.max_cycle, 'long_pair': ids[-1]-ids[0] > cfg.max_pair,
              'cycle_duration_mismatch': duration_ratios[0] > cfg.duration_ratio,
              'corresponding_leg_duration_mismatch': max(duration_ratios[1:]) > cfg.duration_ratio,
              'invalid_amplitude': unit <= 0 or amplitude_ratio is None,
              'amplitude_mismatch': amplitude_ratio is not None and amplitude_ratio > cfg.amplitude_ratio,
              'inefficient_leg': min(p['efficiency'] for p in paths) < cfg.min_leg_efficiency,
              'jump_dominated_leg': max(p['jump_share'] for p in paths) > cfg.max_jump_share,
              'flat_dominated_leg': max(p['flat_share'] for p in paths) > cfg.max_flat_share,
              'too_many_observed_days': len(days) > cfg.max_observed_days,
              'wall_span_too_long': wall_days > cfg.max_wall_days,
              'confirmation_too_late': delay > cfg.max_confirmation_delay}
    reasons.extend(k for k, failed in checks.items() if failed)
    if unit > 0:
        steps = [(x[2]-x[0])/unit, (x[4]-x[2])/unit, (x[3]-x[1])/unit]
        spans = [(max(x[::2])-min(x[::2]))/unit, abs(steps[2])]
        direction = direction_versions(steps, spans, cfg)
    else:
        steps = spans = None
        direction = {'D0': 'uncertain', 'D1': 'uncertain', 'D1_reason': 'invalid_amplitude', 'changed_from_D0': False}
    geometry = fit_geometry(points, bars, Config(timeframe=cfg.timeframe))
    label = source_record['direction_classification'] if source_record is not None else direction['D1']
    known = bars[confirm].get('effective_information_time') or max(v.get('available_at', v['timestamp']) for v in bars[:confirm+1])
    identity = {'source': source, 'cfg': cfg.config_hash, 'pivots': [p['pivot_id'] for p in points]}
    out = {'schema_version': SCHEMA, 'record_id': stable_id('pair', identity), 'config_hash': cfg.config_hash,
           'source': source, 'timeframe': cfg.timeframe, 'instrument': '000852.SH',
           'scale_id': stable_id('time_scale', asdict(cfg)), 'phase': points[0]['kind'],
           'pivot_ids': [p['pivot_id'] for p in points], 'points': copy.deepcopy(points),
           'cycle_ids': [stable_id('complete_cycle', [p['pivot_id'] for p in points[k:k+3]]) for k in (0, 2)],
           'five_occurrence_bars': ids, 'start_bar': ids[0], 'end_bar': ids[-1],
           'start_time': bars[ids[0]]['timestamp'], 'end_time': bars[ids[-1]]['timestamp'],
           'confirmation_bar': confirm, 'confirmation_time': bars[confirm]['timestamp'],
           'effective_information_time': known, 'known_at': known,
           'bar_end_assumed': any(p.get('bar_end_assumed', False) for p in points),
           'leg_durations': legs, 'cycle_durations': cycles, 'pair_duration': ids[-1]-ids[0],
           'duration_ratios': duration_ratios, 'detrended_amplitudes_price': amplitudes,
           'amplitude_ratio': amplitude_ratio, 'amplitude_unit_price': unit, 'leg_paths': paths,
           'observed_trading_days': len(days), 'wall_days': wall_days, 'confirmation_delay_bars': delay,
           'scale_qualified': not reasons, 'scale_rejection_reasons': reasons,
           'phase_steps_in_amplitude_units': steps, 'phase_spans_in_amplitude_units': spans,
           'direction_versions': direction, 'geometric_direction_diagnostic': label,
           'classification': label if not reasons else 'not_same_scale',
           'geometry_log_diagnostic': geometry, 'source_C1_record_id': source_record.get('direction_record_id') if source_record else None,
           'source_C1_classification': source_record.get('direction_classification') if source_record else None,
           'selected': False, 'overlap_suppressed_by': None,
           'trade_authority': False, 'human_reference': False, 'future_outcome_used': False}
    return out


class ExclusiveLedger:
    """Greedy causal packing, never clipping or ranking by direction/fit/outcome."""
    def __init__(self):
        self.records = []
        self.selected = []
        self.closed_partition = []
        self.events = []
        self._end = -1

    def add(self, record):
        r = copy.deepcopy(record)
        if self.records and r['confirmation_bar'] <= self.records[-1]['confirmation_bar']:
            raise ValueError('one candidate per strictly increasing confirmation bar required')
        if r['scale_qualified'] and r['start_bar'] >= self._end:
            r['selected'] = True
            common = {'known_at': r['known_at'], 'confirmation_bar': r['confirmation_bar'], 'provisional': False}
            if r['start_bar'] >= self._end + 1:
                self.closed_partition.append({'first_bar': self._end+1, 'last_bar': r['start_bar'],
                                              'label': 'uncovered', 'record_id': None, **common})
            self.closed_partition.append({'first_bar': r['start_bar']+1, 'last_bar': r['end_bar'],
                                          'label': r['classification'], 'record_id': r['record_id'], **common})
            self._end = r['end_bar']
            self.selected.append(copy.deepcopy(r))
            self.events.append({'confirmation_bar': r['confirmation_bar'], 'confirmation_time': r['confirmation_time'],
                                'effective_information_time': r['known_at'], 'record_id': r['record_id'],
                                'label': r['classification'], 'historical_start_exclusive': r['start_bar'],
                                'historical_end_inclusive': r['end_bar'], 'event_only_not_current_state': True})
        elif r['scale_qualified']:
            r['overlap_suppressed_by'] = self.selected[-1]['record_id']
        self.records.append(copy.deepcopy(r))
        return r

    def partition(self, n_bars):
        if n_bars < self._end + 1:
            raise ValueError('cannot render a partition shorter than published history')
        out = copy.deepcopy(self.closed_partition)
        if n_bars > self._end + 1:
            out.append({'first_bar': self._end+1, 'last_bar': n_bars-1, 'label': 'unresolved_tail',
                        'record_id': None, 'known_at': None, 'confirmation_bar': None, 'provisional': True})
        return out


class TimeEngine(Engine):
    """Reuse only frozen OHLC validation and clock helpers, NOT its ZigZag update.

    Three strictly opposite adjacent close moves confirm the running extremum.
    A duration reset breaks the entire pairing chain and left-censors the restart.
    """
    def __init__(self, config=None):
        self.shape_config = config or ScaleConfig()
        super().__init__(Config(timeframe=self.shape_config.timeframe))
        self.ledger = ExclusiveLedger()
        self.resets = []
        self._chain = []
        self._mode = None
        self._run = 0
        self._last_sign = 0
        self._candidate_point = None
        self._boot_low = self._boot_high = None
        self._last_pivot_bar = None
        self._epoch = 0

    def _point(self, bar, kind):
        return {'kind': kind, 'occurrence_bar': bar['bar_index'], 'occurrence_time': bar['timestamp'],
                'price': bar['close'], 'log_price': bar['log_close']}

    def _confirm(self, point, bar, censored=False):
        p = {**point, 'left_censored': censored, 'confirmation_bar': bar['bar_index'],
             'confirmation_time': bar['timestamp'], 'effective_information_time': bar['effective_information_time'],
             'confirmation_delay_bars': bar['bar_index']-point['occurrence_bar'],
             'bar_end_assumed': self._bar_end_assumed, 'epoch': self._epoch}
        p['pivot_id'] = stable_id('time_pivot', [self.shape_config.config_hash, p])
        self.pivots.append(p); self._last_pivot_bar = point['occurrence_bar']
        if censored:
            return
        self._chain.append(p)
        if len(self._chain) >= 5:
            r = evaluate_pair(self._chain[-5:], self.bars, self.shape_config)
            self.ledger.add(r)

    def _reset(self, bar):
        self.resets.append({'bar': bar['bar_index'], 'time': bar['timestamp'], 'known_at': bar['effective_information_time'],
                            'reason': 'unfinished_leg_exceeded_duration', 'previous_pivot_bar': self._last_pivot_bar})
        self._epoch += 1; self._chain = []; self._mode = None; self._run = self._last_sign = 0
        self._last_pivot_bar = None; self._candidate_point = None
        self._boot_low = self._point(bar, 'low'); self._boot_high = self._point(bar, 'high')

    def update(self, supplied):
        bar, dt, available = self._normalize(supplied)
        self._availability = max(self._availability, available) if self._availability else available
        self._last_dt = dt; self._bar_end_assumed |= bar['bar_end_assumed']
        bar['effective_information_time'] = self._availability.isoformat()
        if supplied.get('trading_day') is not None:
            bar['trading_day'] = str(supplied['trading_day'])
        self.bars.append(bar)
        before = len(self.ledger.records)
        if self._boot_low is None:
            self._boot_low = self._point(bar, 'low'); self._boot_high = self._point(bar, 'high')
            return []
        cfg = self.shape_config
        if self._last_pivot_bar is not None and bar['bar_index']-self._last_pivot_bar > cfg.max_unfinished_leg:
            self._reset(bar)
            return []
        change = bar['close'] - self.bars[-2]['close']
        sign = 1 if change > 0 else -1 if change < 0 else 0
        if self._mode is None:
            if bar['close'] < self._boot_low['price']:
                self._boot_low = self._point(bar, 'low')
            if bar['close'] > self._boot_high['price']:
                self._boot_high = self._point(bar, 'high')
            self._run = self._run+1 if sign and sign == self._last_sign else (1 if sign else 0)
            self._last_sign = sign
            if self._run >= cfg.reversal_bars:
                self._confirm(self._boot_low if sign > 0 else self._boot_high, bar, True)
                self._mode = sign; self._run = 0
                self._candidate_point = self._point(bar, 'high' if sign > 0 else 'low')
        else:
            if self._mode * (bar['close']-self._candidate_point['price']) > 0:
                self._candidate_point = self._point(bar, 'high' if self._mode > 0 else 'low')
            self._run = self._run+1 if sign == -self._mode else 0
            if self._run >= cfg.reversal_bars:
                old_point = self._candidate_point
                self._confirm(old_point, bar)
                self._mode *= -1; self._run = 0
                # Earlier backtracking can contain a more extreme opposite turn
                # than the last three confirming closes. Preserve the entire
                # observed post-extremum path; never seed from current close only.
                after = self.bars[old_point['occurrence_bar']+1:bar['bar_index']+1]
                extreme = max(after, key=lambda b: self._mode*b['close'])
                self._candidate_point = self._point(extreme, 'high' if self._mode > 0 else 'low')
        return copy.deepcopy(self.ledger.records[before:])


def audit_c1_records(records, bars, cfg):
    """C2G: qualify original C1 records without rerunning or renaming its detector."""
    ledger = ExclusiveLedger()
    normalized = []
    latest = None
    for i, b in enumerate(bars):
        latest = max(latest, b.get('available_at', b['timestamp'])) if latest else b.get('available_at', b['timestamp'])
        normalized.append({**b, 'bar_index': i, 'log_close': math.log(b['close']), 'effective_information_time': latest})
    for r in records:
        points = [{'pivot_id': pid, 'kind': r['phase'] if i % 2 == 0 else ('high' if r['phase'] == 'low' else 'low'),
                   'occurrence_bar': j, 'occurrence_time': bars[j]['timestamp'],
                   'price': bars[j]['close'], 'log_price': math.log(bars[j]['close']),
                   'confirmation_bar': r['confirmation_bar'], 'confirmation_time': r['confirmation_time'],
                   'left_censored': False, 'source_pivot_confirmation_not_exported': True}
                  for i, (pid, j) in enumerate(zip(r['pivot_ids'], r['five_occurrence_bars']))]
        # Original C1 export omits individual pivot confirmation clocks. Mark this
        # explicitly; use structure confirmation as an upper bound, not invented clocks.
        pair = evaluate_pair(points, normalized, cfg, source='C2G', source_record=r)
        pair['source_pivot_clock_basis'] = 'structure_confirmation_upper_bound_not_individual_clock'
        ledger.add(pair)
    return ledger
