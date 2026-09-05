#!/usr/bin/env python3
"""Re-run the audited C1 engine via the shared, explicit engine-factory runner."""
from __future__ import annotations
import argparse
import hashlib
import json
import platform
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from run_two_wave_frequency_study import ROOT, replay_study, save
from factor_lab.visual_structure.two_wave.frequency_v031 import DirectionEngine


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',required=True)
    args=parser.parse_args();out=Path(args.output)
    if out.exists() and any(out.iterdir()):raise SystemExit('output must be empty')
    out.mkdir(parents=True,exist_ok=True)
    paths=[Path(__file__),ROOT/'scripts/run_two_wave_frequency_study.py',
           *sorted((ROOT/'src/factor_lab/visual_structure/two_wave').glob('*.py')),
           ROOT/'docs/research/two_wave_5m_separation_protocol_v03.md',ROOT/'data/manifest.json']
    hashes={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
    try:commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,stderr=subprocess.DEVNULL,text=True).strip()
    except (subprocess.CalledProcessError,FileNotFoundError):commit=None
    manifest={'python':platform.python_version(),'actual_git_commit':commit,'source_sha256':hashes,
              'started_at_utc':datetime.now(timezone.utc).isoformat(),'engine_revision':'C1_0.3.1',
              'stage':'direction_only','pnl_computed':False,'fresh_oos':False}
    save(out/'run_manifest.json',manifest)
    result=replay_study(out,engine_type=DirectionEngine)
    result['status']='C1_range_audited_direction_replayed_not_user_accepted'
    save(out/'direction_summary.json',result)
    assert all(hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==h for name,h in hashes.items())
    manifest.update({'finished_at_utc':datetime.now(timezone.utc).isoformat(),'all_source_hashes_unchanged':True})
    save(out/'run_manifest.json',manifest)


if __name__=='__main__':main()
