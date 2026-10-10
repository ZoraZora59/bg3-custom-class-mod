"""Compare pre-polish Stats gameplay with current source and native VFX receipts."""
from __future__ import annotations
import argparse
import json
import re
from pathlib import Path

from school_visual_polish import BANK, RECEIPT, digest, effect_name, paths, profiles
from sword_cultivator_spec import FOLDER
import xml.etree.ElementTree as ET

REPO = Path(__file__).resolve().parents[1]
SOURCE = REPO / 'mods/EasternSwordCultivator/Source'
VISUAL_FIELDS = {'PrepareEffect', 'CastEffect', 'HitEffect', 'TargetEffect', 'TargetHitEffect',
                 'PositionEffect', 'ImpactEffect', 'TargetGroundEffect', 'Trajectories', 'StatusEffect'}


def stats(directory):
    result = {}
    for path in Path(directory).glob('*.txt'):
        for name, body in re.findall(r'new entry "([^"]+)"\n(.*?)(?=new entry |\Z)', path.read_text(encoding='utf-8'), re.S):
            result[name] = dict(re.findall(r'^data "([^"]+)" "([^"]*)"$', body, re.M))
            for field in ('type', 'using'):
                match = re.search(r'^' + field + r' "([^"]+)"$', body, re.M)
                if match:
                    result[name][field] = match[1]
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--before', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    before = stats(args.before)
    after = stats(SOURCE / 'Public' / FOLDER / 'Stats/Generated/Data')
    changes, gameplay_changes = {}, {}
    for name in before.keys() & after.keys():
        changed = {k: {'before': before[name].get(k), 'after': after[name].get(k)}
                   for k in before[name].keys() | after[name].keys()
                   if before[name].get(k) != after[name].get(k)}
        if changed:
            changes[name] = changed
        if any(k not in VISUAL_FIELDS for k in changed):
            gameplay_changes[name] = {k: v for k, v in changed.items() if k not in VISUAL_FIELDS}
    added, removed = set(after) - set(before), set(before) - set(after)
    expected_statuses = {'ESC_VFX_BLOOD_DOMAIN', 'ESC_VFX_SWORD_DOMAIN'}
    pure_status = all(after.get(name, {}).get('StatusType') == 'BOOST'
                      and not any(after[name].get(f) for f in ('Boosts', 'OnApplyFunctors', 'OnRemoveFunctors', 'TickFunctors'))
                      for name in expected_statuses)
    receipt = json.loads((SOURCE / RECEIPT).read_text(encoding='utf-8'))
    proof = {r['effect_name']: r for r in receipt['records']}
    resources = {n.find('attribute[@id="EffectName"]').get('value'): n
                 for n in ET.parse(SOURCE / BANK).findall('.//node[@id="Resource"]')}
    native_mismatches = []
    for key in profiles():
        editor, binary = paths(key)
        row = proof.get(effect_name(key), {})
        resource = resources.get(effect_name(key))
        if (digest(SOURCE / editor) != row.get('source_sha256')
                or digest(SOURCE / binary) != row.get('compiled_sha256')
                or not row.get('semantic_roundtrip_verified') or resource is None
                or resource.find('attribute[@id="SourceFile"]').get('value') != binary.as_posix()):
            native_mismatches.append(key)
    result = {'success': not gameplay_changes and not removed and added == expected_statuses
              and pure_status and not native_mismatches,
              'evidenceLayer': 'static-native-compilation-and-gameplay-data-comparison',
              'existingStatsGameplayChanges': gameplay_changes, 'addedStats': sorted(added), 'removedStats': sorted(removed),
              'pureVisualDomainStatuses': pure_status, 'visualChanges': changes,
              'effectCount': len(profiles()), 'skillCount': len({p['skill'] for p in profiles().values()}),
              'nativeMismatches': native_mismatches, 'clientVisualTest': 'pending'}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({k: v for k, v in result.items() if k != 'visualChanges'}, ensure_ascii=False, indent=2))
    return 0 if result['success'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
