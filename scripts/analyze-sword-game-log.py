"""Summarize an immutable BG3SE runtime log without claiming gameplay coverage."""
import argparse
import hashlib
import json
import re
from collections import Counter
from pathlib import Path


def analyze(path):
    raw = path.read_bytes()
    text = raw.decode('utf-8-sig', errors='replace')
    errors = Counter()
    for line in text.splitlines():
        if re.search(r'Error while dispatching event|event handler failed:|Error loading|Failed to load', line, re.I):
            errors[line.strip()] += 1
    return {
        'Log': str(path.resolve()),
        'LogSHA256': hashlib.sha256(raw).hexdigest(),
        'Lines': len(text.splitlines()),
        'ServerBridgeLoaded': '[ESC] Server bridge loaded' in text,
        'Errors': [{'Message': line, 'Count': count} for line, count in errors.items()],
        'ErrorCount': sum(errors.values()),
        'RuntimeLogGate': 'fail' if errors else 'no errors detected in this log',
        'Boundary': 'Log analysis only. No class, spell, combat, resource or save/load case is passed by this report.',
    }


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('log', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    report = analyze(args.log)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({key: report[key] for key in ('Lines', 'ServerBridgeLoaded', 'Errors', 'ErrorCount', 'RuntimeLogGate')}, ensure_ascii=False))
