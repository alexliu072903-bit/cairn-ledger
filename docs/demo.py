#!/usr/bin/env python3
"""Render a fictional ledger locally. No transcript access or model calls."""
import argparse
from pathlib import Path
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ledger import render


def demo(output):
    output = output.expanduser().resolve()
    if (output / 'regressions.md').exists():
        raise SystemExit('Output already exists; choose a new --output directory.')
    output.mkdir(parents=True, exist_ok=True)
    examples = [
        ('01', 'scope', '擅自扩大范围', '我只让你比较两种方案，怎么又开始写实现了？', 'codex', '2026-01-12T01:00:00Z'),
        ('02', 'scope', '擅自扩大范围', '这次只处理导出，不要顺便重做设置页。', 'claude', '2026-01-13T02:00:00Z'),
        ('03', 'format', '忽略已有格式', '请沿用项目里的日期格式，不要再换一种。', 'codex', '2026-01-13T03:00:00Z'),
    ]
    events = [dict(event_id='demo-'+n+'-event', category_id=category, category_name=name,
                   quote=quote, source=source, timestamp=at, rule_ref='无对应规则',
                   session_url='#fictional-'+n, source_path='demo-source/'+source+'.jsonl',
                   source_line=int(n), message_id='fictional-message-'+n)
              for n, category, name, quote, source, at in examples]
    status = dict(status='演示数据', pending=0, error=None, at='2026-01-13T03:05:00Z')
    config = dict(vault=str(output), since='2026-01-12T00:00:00Z', sources={'codex': [], 'claude': []})
    state = dict(last_run='2026-01-13T03:05:00Z', added=3,
                 source_status={'codex': status, 'claude': status})
    render(config, state, events)
    target = output / 'regressions.md'
    target.write_text('> 演示：以下消息、时间、次数和定位全部虚构，非真实使用结果。\n\n' + target.read_text())
    print(target)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, help='New directory for the demo output; defaults to a system temp directory')
    args = parser.parse_args()
    demo(args.output or Path(tempfile.mkdtemp(prefix='cairn-ledger-demo-')))
