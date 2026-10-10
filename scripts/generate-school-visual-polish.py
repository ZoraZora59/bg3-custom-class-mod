"""Author per-technique school VFX. Compile separately before enabling bindings."""
from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path

from school_visual_polish import EDITOR, SUBDIRECTORY, authoring_modules, effect_name, profiles
from sword_cultivator_spec import MOD, guid

REPO = Path(__file__).resolve().parents[1]
SOURCE = REPO / 'mods' / MOD / 'Source'
MANIFEST = REPO / 'build/sword-vfx/three-school-polish-20261007/authoring-manifest.json'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data', type=Path, default=Path('E:/SteamLibrary/steamapps/common/Baldurs Gate 3/Data'))
    args = parser.parse_args()
    spec = importlib.util.spec_from_file_location('school_polish_fx', REPO / 'scripts/generate-sword-vfx.py')
    fx = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(fx)
    dictionary = fx.PropertyDictionary(args.data)
    records = []
    for module in authoring_modules():
        for key, profile in module.PROFILES.items():
            root, origins, details = module.author(args.data, key, dictionary)
            from sword_glow import apply as apply_glow
            details.update(apply_glow(root, dictionary, key.split('_')[0]))
            root.set('id', guid('vfx/polish/editor/' + key))
            path = SOURCE / EDITOR / (effect_name(key) + '.lsefx')
            fx.write(path, root)
            records.append({'key': key, **profile, 'effect_name': effect_name(key),
                            'source': str(path.relative_to(SOURCE).as_posix()),
                            'source_sha256': fx.digest(path), 'details': details,
                            'references': [{'path': str(p), 'sha256': fx.digest(p)} for p in origins]})
    if len(records) != len(profiles()):
        raise ValueError('Authoring plan and written profiles differ')
    payload = {'subdirectory': SUBDIRECTORY, 'records': records,
               'property_dictionary': dictionary.evidence(),
               'evidence_layer': 'editor-source-only', 'client_visual_test': 'pending'}
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f'Authored {len(records)} per-technique effects; native compilation pending. Manifest: {MANIFEST}')


if __name__ == '__main__':
    main()
