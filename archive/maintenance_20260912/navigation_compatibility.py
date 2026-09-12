#!/usr/bin/env python3
"""Preserve required Layer-1..4 navigation without restoring stale project indexes."""
from pathlib import Path
import hashlib

p = Path('scripts/repository_consistency.py')
raw = p.read_bytes()
assert hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest() == '89de8edefd46541e969b69b6c9235df34b34772b', 'unexpected renderer input'
s = raw.decode()
old = '    return docs\n\n\ndef classify'
new = '''    for page in ('ai-readme.md', 'README.md', 'docs/00-index.md', 'docs/user/README.md', 'docs/ops/README.md'):
        docs[page] += '\\n## 四层基础设施导航（冻结兼容合同）\\n\\n'
        docs[page] += link(page, 'docs/ops/timing_infrastructure_four_layer_inventory@1.0.json', 'timing_infrastructure_four_layer_inventory@1.0.json') + '\\n\\n'
        docs[page] += '数据时钟 → K线测量 → 策略结构 → 执行标的；层间依赖关系保留，但本仓不获得 Layer 4 执行授权。\\n\\n'
        docs[page] += link(page, 'docs/ops/timing_layer1_datahub_clock_split@1.0.json', '数据时钟合同') + ' / '
        docs[page] += link(page, 'docs/ops/timing_layer2_measurement_plane@2.3.json', 'K线测量合同') + ' / '
        docs[page] += link(page, 'docs/ops/timing_layer3_strategy_architecture@2.2.json', '策略结构合同') + '\\n'
    return docs


def classify'''
assert s.count(old) == 1, 'renderer patch context drift'
p.write_text(s.replace(old, new), encoding='utf-8')
