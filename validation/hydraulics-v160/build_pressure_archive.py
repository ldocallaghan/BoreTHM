"""Build the scientific pressure archive from completed comparison tables."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import platform

import iapws
import numpy
import scipy

ROOT = Path(__file__).resolve().parents[2]


def read_csv(path):
    with path.open(newline='', encoding='utf-8') as stream:
        return list(csv.DictReader(stream))


def write_csv(path, rows):
    fields = list(dict.fromkeys(key for row in rows for key in row))
    with path.open('w', newline='', encoding='utf-8') as stream:
        writer = csv.DictWriter(stream, fields, lineterminator='\n')
        writer.writeheader()
        writer.writerows(rows)


def digest(path):
    data = path.read_bytes()
    if path.suffix != '.png':
        data = data.replace(b'\r\n', b'\n')
    return hashlib.sha256(data).hexdigest()


def build(source, output):
    output.mkdir(parents=True, exist_ok=True)
    names = ('development-windows.csv', 'development-events.csv', 'development-bha.csv')
    for name in names:
        rows = read_csv(source / name)
        write_csv(output / name, [{k: v for k, v in row.items() if k != 'duration_s'} for row in rows])
    for path in sorted(source.glob('development-*')):
        if path.suffix in ('.png', '.svg'):
            data = path.read_bytes()
            (output / path.name).write_bytes(data.replace(b'\r\n', b'\n') if path.suffix == '.svg' else data)

    archived_b = {row['sample']: float(row['model_spp_psi'])
                  for row in read_csv(ROOT / 'validation/forge16b/s2b/pressure-samples.csv')
                  if row['rheology_case'] == 's2_revised'}
    archived_a = {}
    with (ROOT / 'validation/forge16b/s2/results.jsonl').open(encoding='utf-8') as stream:
        for line in stream:
            row = json.loads(line)
            if row['well'] == '16A' and row['rheology_case'] == 'blind_original':
                archived_a[row['sample']] = row['spp'] / 6894.757
    controls = []
    for row in read_csv(output / names[0]):
        if row['variant'] != 'v1.5.0-26.7' or row['status'] != 'ok':
            continue
        well = row['well']
        old = (archived_a if well == '16A' else archived_b)[row['window_id']]
        now = float(row['predicted_low_psi'])
        controls.append(dict(well=well, bha=row['bha'], window_id=row['window_id'],
            archived_prediction_psi=old, replay_prediction_psi=now, difference_psi=now-old,
            archive_source='validation/forge16b/s2/results.jsonl:spp/6894.757' if well == '16A'
                           else 'validation/forge16b/s2b/pressure-samples.csv:model_spp_psi'))
    write_csv(output / 'legacy-reproduction.csv', controls)
    source_names = (
        'validation/forge16b/s2/plan.json', 'validation/forge16b/s2b/pressure-samples.csv',
        'validation/forge16b/s2/results.jsonl', 'validation/hydraulics-v160/build_pressure_archive.py',
        'src/borethm/studies/pressure_comparison.py', 'src/borethm/model1_coupled.py',
        'src/borethm/hydraulic_losses.py', 'src/borethm/programme.py', 'src/borethm/fluids.py',
        'src/borethm/studies/forge16_energy.py', 'src/borethm/studies/validate_forge16a.py',
        'src/borethm/studies/validate_forge16b.py', 'src/borethm/studies/validate_forge16b_wholewell.py')
    manifest = dict(
        description='FORGE development-data pressure comparisons; no held-out pressure observations',
        checksum_convention='SHA256; text normalised to LF newlines, binary images unchanged',
        physical_code_commit='8e6d0b9', comparison_entry_point_commit='a1cb3cb',
        runtime=dict(python=platform.python_version(), numpy=numpy.__version__,
                     scipy=scipy.__version__, iapws=iapws.__version__),
        fixed_inputs='Registered 16A blind-original and 16B S2-revised samples and previously fitted thermal parameters; no refitting',
        variants=['v1.5.0-26.7', 'v1.5.0-48.9', 'v1.6.0-48.9'],
        source_sha256={name: digest(ROOT / name) for name in source_names},
        results_sha256={p.name: digest(p) for p in sorted(output.iterdir())
                       if p.suffix in ('.csv', '.svg', '.png')})
    (output / 'manifest.json').write_bytes((json.dumps(manifest, indent=2)+'\n').encode('utf-8'))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--output', type=Path, default=Path(__file__).parent / 'pressure-comparisons')
    args = parser.parse_args()
    build(args.source, args.output)


if __name__ == '__main__':
    main()
