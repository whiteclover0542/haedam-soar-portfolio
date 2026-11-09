"""Build a new local pfSense handoff directory. Never contacts or changes a device."""

import argparse
import hashlib
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
APPROVED_SHA = 'f0eea2979466537f1ef45db85df3caf378732824d6255f851a7e8af30a3553ed'
SOURCES = {'pfsense_response.py': 'lab/pfsense/pfsense_response.py',
           'pfsense-response.schema.json': 'contracts/pfsense-response.schema.json',
           'install_bundle.py': 'lab/pfsense/install_bundle.py', 'INSTALL.md': 'lab/pfsense/INSTALL.md'}


def build(output, root=ROOT):
    payload = {name: (Path(root) / source).read_bytes() for name, source in SOURCES.items()}
    hashes = {name: hashlib.sha256(content).hexdigest() for name, content in payload.items()}
    if hashes['pfsense_response.py'] != APPROVED_SHA:
        raise ValueError('Candidate differs from the approved PR64 tool; review version first.')
    for name in ('install_bundle.py', 'pfsense_response.py'):
        compile(payload[name], name, 'exec')
    json.loads(payload['pfsense-response.schema.json'])
    output = Path(output)
    if not output.parent.is_dir():
        raise ValueError('Output parent must already exist.')
    output.mkdir()  # Exclusive: an existing directory is never reused.
    for name, content in payload.items():
        with (output / name).open('xb') as stream:
            stream.write(content)
    manifest = {'version': 1, 'tool_sha256': APPROVED_SHA, 'files': hashes,
                'status': 'prepared_not_deployed', 'target': '203.0.113.22',
                'source_review': 'PR64 tool 6b30d1045f4f225621dabea9b8c98499f257990f',
                'requires': ['agreed_test_window', 'D_dedicated_public_key', 'forced_command_and_source_limit',
                             'D_to_pfsense_22_path', 'C_D_active_owner_contract', 'live_effect_and_restore']}
    # Completion marker last; an interrupted directory is never accepted as a complete release.
    with (output / 'bundle.json').open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(manifest, stream, ensure_ascii=False, indent=2, sort_keys=True)
        stream.write('\n')
    return manifest


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', required=True, type=Path, help='new local directory')
    args = parser.parse_args(argv)
    try:
        manifest = build(args.out)
        print(json.dumps({'ok': True, 'status': manifest['status'], 'files': len(manifest['files']),
                          'tool_sha256': manifest['tool_sha256']}, sort_keys=True))
        return 0
    except (OSError, ValueError, SyntaxError):
        print('Bundle not completed; existing paths and device state were not changed.', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
