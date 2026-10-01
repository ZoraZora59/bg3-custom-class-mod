"""Read a Toolkit log without treating unrelated game/editor noise as mod errors.

Usage: python scripts/analyze-sword-toolkit-log.py --log PATH [--output PATH]
Exit 0 requires no directly attributable ESC diagnostic and no native crash.
This does not certify class creation, progression, Script Extender, or gameplay.
"""
import argparse
import json
import re
import sys
from pathlib import Path

MODULE = re.compile(r'(?i)(?:EasternSwordCultivator|ESC_[A-Za-z0-9_]+|ClassESC_[A-Za-z0-9_]+)')
IMAGE = re.compile(r"(?i)(?:Assets|AssetsLowRes)/[A-Za-z0-9_./-]*?(?:ESC_[A-Za-z0-9_]+|ClassEasternSwordCultivator)[A-Za-z0-9_./-]*\.(?:png|dds)")
SPELL = re.compile(r'\(Spell ID:\s*([A-Za-z0-9_]+)\)')
ERROR = re.compile(r'(?i)(?:!ASSERT!|!ERROR!|!CRITICAL!|\berror\b|missing|not found|cannot|couldn.t find|unsupported|invalid)')
PARSER = re.compile(r'(?i)(?:StatParser|StatsParser|ParseDataLine|GSTNodeStorage|StatsObject::SetValue)')
CRASH = re.compile(r'(?i)(?:EXCEPTION_ACCESS_VIOLATION|An unhandled exception has occurred)')


def analyze_lines(lines, log_path):
    issues = {}
    crash_evidence = []
    frames = []
    in_stack = False
    line_count = 0
    for number, line in enumerate(lines, 1):
        line_count = number
        line = line.rstrip('\r\n')
        if CRASH.search(line):
            crash_evidence.append({'path': str(log_path), 'line': number, 'text': line})
        if line == 'StackTrace:':
            in_stack = True
        elif line == '[Managed]':
            in_stack = False
        elif in_stack and ('Noesis::' in line or 'UninstallGameUI' in line or 'VMDamageRoll' in line):
            frames.append({'path': str(log_path), 'line': number, 'text': line})

        image = IMAGE.search(line)
        spell = SPELL.search(line)
        if image and ERROR.search(line):
            kind, identity = 'missing_image', image.group(0)
        elif spell and MODULE.search(spell.group(1)) and ('Stats description parameters do not support' in line or 'StatsDescriptionHelper' in line and ERROR.search(line)):
            kind, identity = 'conditional_tooltip_damage', spell.group(1)
        elif 'No UUID condition error object is configured' in line and MODULE.search(line):
            kind, identity = 'missing_condition_error_mapping', MODULE.search(line).group(0)
        elif MODULE.search(line) and PARSER.search(line) and ERROR.search(line):
            kind, identity = 'stat_parser', MODULE.search(line).group(0)
        elif MODULE.search(line) and ERROR.search(line):
            kind, identity = 'module_other', MODULE.search(line).group(0)
        else:
            continue
        key = (kind, identity.casefold())
        entry = issues.setdefault(key, {'kind': kind, 'identity': identity, 'occurrences': 0, 'evidence': []})
        entry['occurrences'] += 1
        entry['evidence'].append({'path': str(log_path), 'line': number, 'text': line})

    crashed = bool(crash_evidence)
    grouped = sorted(issues.values(), key=lambda row: (row['kind'], row['identity'].casefold()))
    return {'Log': str(log_path), 'Lines': line_count, 'ModuleIssues': grouped,
            'NativeCrash': {'Detected': crashed, 'Attribution': 'unresolved' if crashed else None,
                            'Evidence': crash_evidence, 'RelevantStackFrames': frames},
            'ModuleErrorGate': 'fail' if grouped else 'no-attributable-errors-observed',
            'ProcessExitGate': 'fail-native-crash' if crashed else 'no-crash-in-log-observed',
            'ToolkitLogGate': 'fail' if grouped or crashed else 'no-attributable-errors-observed',
            'Boundary': 'Read-only log classification; no Toolkit or game behavior is proven by this parser.'}


def analyze_log(path):
    path = Path(path).resolve(strict=True)
    with path.open('r', encoding='utf-8', errors='replace') as source:
        return analyze_lines(source, path)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--log', type=Path, required=True, help='Saved Toolkit log file')
    parser.add_argument('--output', type=Path, help='Optional JSON report path')
    args = parser.parse_args(argv)
    try:
        result = analyze_log(args.log)
    except (OSError, ValueError) as exc:
        parser.error(str(exc))
    rendered = json.dumps(result, ensure_ascii=False, indent=2) + '\n'
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding='utf-8')
    else:
        sys.stdout.write(rendered)
    return 0 if result['ToolkitLogGate'] != 'fail' else 1


if __name__ == '__main__':
    raise SystemExit(main())
