"""Assemble the benchmark dataset from retained files and input definitions.

No evaluation, calibration or numerical solver is called. The only function
sampling tabulates the built-in geotherms on retained programme depth grids.
"""
import argparse
import csv
from dataclasses import asdict
import hashlib
import importlib
import io
import json
from pathlib import Path
import zipfile

from borethm import site_evaluation as se

ROOT = Path(__file__).resolve().parents[1]
VERSION = '1.0'
INPUT_COMMIT = '7ae63cf59e198b7af573282f2aad57d4b40e5a05'
CASES = {
    'ut-austin': ('benchmark_utaustin.json', 'benchmark_utaustin'),
    'forge-circulation': ('validate_forge16b.json', 'validate_forge16b'),
    'forge-pauses': ('forge_pauses.json', 'validate_forge_pauses'),
    'soultz-crosscheck': ('soultz_crosscheck_v122.json', 'crosscheck_soultz'),
    'site-reference-v134': ('v134_site_table.json', 'release_v134'),
    'breakout-timing-v136': ('v136_breakout_timing.json', 'levers'),
}
ATTRIBUTES = {
    'ut-austin': {
        'borethm.studies.benchmark_utaustin': (
            'MUD', 'RHO_WATER_INLET', 'GPM', 'T_SURF', 'K_ROCK', 'RHOCP_ROCK',
            'TVD', 'T_INLET', 'EXPOSURE', 'FIG2', 'SPP_600'),
        'borethm.well_geometry': ('WU_L_HWDP', 'WU_L_COLLAR', 'WU_L_BIT', 'WU_SHOES',
                                  'K_STEEL', 'K_CEMENT'),
    },
    'forge-circulation': {
        'borethm.studies.validate_forge16b': (
            'FT', 'INCH', 'GPM', 'PSI', 'K_ROCK', 'RHOCP_ROCK', 'K_ROCK_RANGE',
            'MWD_ABOVE_BIT_FT', 'HWDP_JOINT_FT', 'BHA12_REGULAR_FT', 'NOZZLES', 'DEPTHS'),
    },
    'forge-pauses': {
        'borethm.studies.validate_forge_pauses': (
            'PUMPS_ON_GPM', 'ON_BOTTOM_FT', 'K_IDP_UNFITTED', 'DZ_FT', 'SHOE_FT',
            'R_OPEN', 'R_CASED', 'RUN_ENDS'),
    },
    'soultz-crosscheck': {
        'borethm.studies.crosscheck_soultz': (
            'Z_CHECK', 'COOLING_K', 'OBS_ONSET_FIRST', 'OBS_ONSET_DENSE',
            'OBS_DITF_CONTINUOUS_TO', 'STRENGTHS'),
    },
}
INPUT_UNITS = {
    'ut-austin': dict(MUD=dict(rho='kg/m3', cp='J/(kg K)', mu='Pa s', k='W/(m K)'),
        RHO_WATER_INLET='kg/m3', GPM='m3/s per US gal/min', T_SURF='degrees C',
        K_ROCK='W/(m K)', RHOCP_ROCK='J/(m3 K)', TVD='m', T_INLET='degrees C',
        EXPOSURE='s', FIG2='degrees C', SPP_600='MPa', WU_L_HWDP='m', WU_L_COLLAR='m',
        WU_L_BIT='m', WU_SHOES='m', K_STEEL='W/(m K)', K_CEMENT='W/(m K)',
        pipe_layers=dict(r_in='m', r_out='m', k='W/(m K)', joint_fraction='dimensionless'),
        run_defaults=dict(G_per_km='degrees C/km', gpm='US gal/min', friction_heat='boolean')),
    'forge-circulation': dict(FT='m/ft', INCH='m/in', GPM='m3/s per US gal/min', PSI='Pa/psi',
        K_ROCK='W/(m K)', RHOCP_ROCK='J/(m3 K)', K_ROCK_RANGE='W/(m K)',
        MWD_ABOVE_BIT_FT='ft', HWDP_JOINT_FT='ft', BHA12_REGULAR_FT='ft',
        NOZZLES='diameters in 1/32 in', DEPTHS='ft measured depth'),
    'forge-pauses': dict(PUMPS_ON_GPM='US gal/min', ON_BOTTOM_FT='ft',
        K_IDP_UNFITTED='W/(m K)', DZ_FT='ft', SHOE_FT='ft', R_OPEN='m', R_CASED='m',
        RUN_ENDS='Unix seconds; source clock interpreted as UTC'),
    'soultz-crosscheck': dict(Z_CHECK='m TVD', COOLING_K='K', OBS_ONSET_FIRST='m TVD',
        OBS_ONSET_DENSE='m TVD', OBS_DITF_CONTINUOUS_TO='m TVD', STRENGTHS='(label, UCS values in Pa)'),
    'site-reference-v134': dict(site_profiles='../sites/units.json',
        programme='fields retain the explicit unit names and flow_unit in each evidence record'),
    'breakout-timing-v136': dict(flow_L_s='L/s', shoe_m='m', pv_fraction='dimensionless',
        bhp_Pa='Pa', coating_rating_C='degrees C', allowance_SG='SG equivalent',
        pipe='PipeType name', form_h='h', scan_minutes='min'),
}


def encoded(value):
    return (json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + '\n').encode('utf-8')


def code_reference(module, name=None):
    path = 'src/' + module.replace('.', '/') + '.py'
    return dict(module=module, name=name, path=path,
                url=f'https://github.com/ldocallaghan/BoreTHM/blob/{INPUT_COMMIT}/{path}')


def tolerance_record(case):
    """Describe existing assertions; untested diagnostics get no new threshold."""
    records = {
        'ut-austin': dict(source='tests/test_benchmark_utaustin.py::test_benchmark_table_is_unchanged',
            units=dict(temperature='degrees C', spp_MPa='MPa'),
            rules=[dict(fields='all numeric fields', absolute=0.5)],
            note='Regression tolerance only; it does not assert agreement with Wu et al.'),
        'forge-circulation': dict(source='tests/test_validate_forge16b.py',
            units=dict(temperature='degrees F', decomposition='degrees F difference',
                       k_idp='W/(m K)', film_mult='dimensionless'),
            rules=[dict(fields='film_mult', absolute=0.02),
                   dict(fields='k_idp and unfitted/k_idp', relative=0.03),
                   dict(fields='run_means, bha12_late and their unfitted counterparts', absolute=1.0),
                   dict(fields='decomposition (fitted chain)', absolute=1.0)],
            note='Unfitted decomposition is retained without a separate numerical acceptance assertion.'),
        'forge-pauses': dict(source='tests/test_forge_pauses.py::test_pause_check_is_unchanged',
            units=dict(f='dimensionless', f_no_node='dimensionless', start='Unix seconds, UTC convention',
                       hours='h', obs='degrees F anomaly', mod='degrees F anomaly', pred='degrees F anomaly'),
            rules=[dict(fields='f and f_no_node', absolute=0.02),
                   dict(fields='rows and rows_no_node: obs', absolute=0.5),
                   dict(fields='rows and rows_no_node: mod', absolute=1.0)],
            note='pred values are retained; the existing numerical regression does not set their tolerance.'),
        'soultz-crosscheck': dict(source='tests/test_soultz_crosscheck.py::test_results_are_unchanged_from_v122',
            units=dict(ucs='MPa', cooling='K', width='degrees', onset='m TVD'),
            rules=[dict(fields='width', absolute=0.001),
                   dict(fields='source, ucs, cooling, onset and verdicts', exact=True)],
            note='Onsets use the retained 10 m search grid. Null means no onset in the searched interval.'),
        'site-reference-v134': dict(source='src/borethm/studies/release_v134.py::assert_reviewed',
            units=dict(target_m='m', bit_C='degrees C', weights_SG='surface SG at 20 degrees C',
                       window_bounds='surface SG at 20 degrees C', md='m measured depth'),
            rules=[dict(match='boolean, string or null', exact=True),
                   dict(match='numeric path contains /settings/', absolute=1e-8,
                        exception='/bhp_Pa uses 1 Pa'),
                   dict(match='numeric path contains _SG', absolute=0.002),
                   dict(match='numeric path contains _C', absolute=0.1),
                   dict(match='numeric path contains _Pa', absolute=10000.0),
                   dict(match='numeric path ends /md', absolute=100.0),
                   dict(match='numeric path ends /target_m', absolute=0.1),
                   dict(match='other numeric values', absolute=1e-8)],
            note='Rules are evaluated in the listed order. Provenance is outside physical comparisons.'),
        'breakout-timing-v136': dict(source='tests/test_breakout_timing.py',
            units=dict(drill_SG='SG-equivalent at target, including connection checks',
                       drill_rho_surface='kg/m3 at 20 degrees C', window_lo_hi='kg/m3 at 20 degrees C',
                       md='m measured depth', delay_min='min', form_h='h'),
            rules=[dict(fields='z_m and window bound md', absolute=0.01),
                   dict(fields='drill_SG', absolute=0.002),
                   dict(fields='drill_rho_surface and window lo/hi divided by 1000', absolute=0.002),
                   dict(fields='settings, case labels, UCS, states, verdicts, open flags and scan brackets', exact=True)],
            note='The fixed scan grid is not a measured breakout formation time.'),
    }
    return records[case]


def build_files(root=ROOT):
    """Return all dataset bytes, including provenance and manifest."""
    root = Path(root)
    files, origins = {}, {}

    def put(name, content, origin):
        files[name] = content
        origins[name] = origin

    def generated(name, value, **origin):
        put(name, encoded(value), dict(kind='generated', **origin))

    def copy(source, target, licence='CC-BY-4.0'):
        content = (root / source).read_bytes()
        old_path = source.replace('src/borethm/data/', 'data/')
        put(target, content, dict(kind='copy', path=source,
            source_release='v1.3.6', original_path=old_path, licence=licence,
            sha256=hashlib.sha256(content).hexdigest()))

    for path in sorted((root / 'benchmarks').rglob('*.md')):
        name = path.relative_to(root / 'benchmarks').as_posix()
        put(name, path.read_bytes(), dict(kind='documentation', licence='CC-BY-4.0'))
    copy('LICENSE-docs', 'LICENSE')
    put('NOTICE', (root / 'benchmarks/NOTICE').read_bytes(), dict(kind='documentation', licence='CC-BY-4.0'))

    for path in sorted((root / 'src/borethm/data').rglob('*')):
        if not path.is_file() or 'raw' in path.parts or path.suffix not in ('.csv', '.json', '.md'):
            continue
        relative = path.relative_to(root / 'src/borethm/data').as_posix()
        licence = 'Open Government Licence' if relative.startswith('ud1/') and path.suffix == '.csv' else 'CC-BY-4.0'
        copy(path.relative_to(root).as_posix(), 'data/' + relative, licence)

    sites = se.named_sites()
    generated('sites/units.json', dict(depths='m', temperatures='degrees C',
        Sv_grad='Pa/m', rho_fluid_grad='Pa/m', K0_min='dimensionless', SHmax_over_Sv='dimensionless',
        k_rock='W/(m K)', E_rock='Pa', UCS='Pa', strength_cases='(label, UCS in Pa)',
        mu='dimensionless', stress_cases=dict(gradients='Pa/m', stress_intercepts='Pa',
                                            Pp_datum='m', z_data='m', mu='dimensionless')),
        source=code_reference('borethm.site_evaluation', 'SiteProfile and StressProfile'), licence='CC-BY-4.0')
    for key, site in sites.items():
        profile = asdict(site)
        checkpoint = f'results/v1.3.4/checkpoint-1/{key}.json'
        saved = json.loads((root / checkpoint).read_text())
        depths = saved['windows']['depths']
        functions = {name: value for name, value in profile.items() if callable(value)}
        for name, function in functions.items():
            profile[name] = dict(callable=code_reference(function.__module__, function.__qualname__),
                                 samples=f'{key}-geotherms.csv', column=name + '_C')
        generated(f'sites/{key}.json', profile, method='dataclasses.asdict; callable fields described separately',
                  source=code_reference('borethm.site_evaluation' if key == 'soultz' else 'borethm.comparative_sites'),
                  licence='CC-BY-4.0')
        table = io.StringIO(newline='')
        writer = csv.writer(table, lineterminator='\n')
        writer.writerow(['depth_m', *(name + '_C' for name in functions)])
        for depth in depths:
            writer.writerow([depth, *(float(function(depth)) for function in functions.values())])
        put(f'sites/{key}-geotherms.csv', table.getvalue().encode('utf-8'),
            dict(kind='tabulation', grid_source=checkpoint, grid_pointer='/windows/depths',
                 functions={name: code_reference(f.__module__, f.__qualname__) for name, f in functions.items()},
                 depth_unit='m; MD equals TVD in these vertical site designs', temperature_unit='degrees C',
                 licence='CC-BY-4.0'))

    for case, (golden, module) in CASES.items():
        copy('tests/golden/' + golden, case + '/expected.json')
        source = code_reference('borethm.studies.' + module)
        inputs = dict(site_profiles='../sites/', data='../data/', code=source,
                      units=INPUT_UNITS[case], attributes={})
        for module_name, names in ATTRIBUTES.get(case, {}).items():
            current = importlib.import_module(module_name)
            inputs['attributes'][module_name] = {name: getattr(current, name) for name in names}
        if case == 'ut-austin':
            benchmark = importlib.import_module('borethm.studies.benchmark_utaustin')
            inputs['pipes'] = {name: asdict(pipe) for name, pipe in benchmark.PIPES.items()}
            inputs['whole_wall_pipes'] = {name: asdict(pipe) for name, pipe in benchmark.WHOLE_WALL.items()}
            inputs['geometry_recipes'] = [code_reference('borethm.studies.benchmark_utaustin', 'well'),
                                           code_reference('borethm.well_geometry', 'wu2025_well')]
            inputs['run_defaults'] = dict(source=code_reference('borethm.studies.benchmark_utaustin', 'run'),
                                           G_per_km=24.0, gpm=600.0, friction_heat=True)
        if case in ('forge-circulation', 'forge-pauses'):
            inputs['geometry_recipes'] = [code_reference('borethm.studies.validate_forge16b', name)
                                           for name in ('hole', 'string', 'survey', 'formation_temperature')]
        if case == 'site-reference-v134':
            inputs['programmes'] = {}
            for key in sites:
                source_path = f'results/v1.3.4/checkpoint-1/{key}.json'
                copy(source_path, f'{case}/evidence/{key}.json')
                inputs['programmes'][key] = dict(path=f'evidence/{key}.json',
                                                 pointers=['/site', '/programme', '/windows/depths'])
        if case == 'breakout-timing-v136':
            retained = json.loads((root / 'tests/golden/v136_breakout_timing.json').read_text())
            inputs['paired_settings'] = {key: {delay: row['settings'] for delay, row in pairs.items()}
                                         for key, pairs in retained['pairs'].items()}
            inputs['scan_minutes'] = {key: row['scan_minutes'] for key, row in retained['scans'].items()}
            for name, digest in retained['provenance']['evidence_sha256'].items():
                path = 'results/v1.3.6/breakout-timing/' + name
                assert hashlib.sha256((root / path).read_bytes()).hexdigest() == digest, path
                copy(path, f'{case}/evidence/{name}')
        generated(case + '/inputs.json', inputs, source=source, licence='CC-BY-4.0')
        generated(case + '/tolerances.json', tolerance_record(case),
                  source='existing regression assertions named in the record', licence='CC-BY-4.0')

    files['sources.json'] = encoded(dict(dataset_version=VERSION,
        input_definition_commit=INPUT_COMMIT, retained_release='v1.3.6', files=dict(sorted(origins.items())),
        note='Copied files retain their original provenance; no model outputs were regenerated.'))
    files['manifest.json'] = encoded(dict(dataset_version=VERSION, cases=list(CASES),
        hash_algorithm='SHA-256',
        note='Hashes cover every dataset file except this manifest itself.',
        files={name: hashlib.sha256(content).hexdigest() for name, content in sorted(files.items())}))
    return files


def assemble(output, archive, root=ROOT):
    output, archive = Path(output).resolve(), Path(archive).resolve()
    if archive.is_relative_to(Path(root).resolve()) or archive.is_relative_to(output):
        raise ValueError('write the upload ZIP outside the repository and dataset directory')
    files = build_files(root)
    if output.exists():
        extra = {p.relative_to(output).as_posix() for p in output.rglob('*') if p.is_file()} - files.keys()
        if extra:
            raise ValueError('unrecognised files in output directory: ' + ', '.join(sorted(extra)))
    for name, content in files.items():
        path = output / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
    archive.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as bundle:
        for name, content in sorted(files.items()):
            entry = zipfile.ZipInfo(f'borethm-benchmarks-{VERSION}/{name}', date_time=(1980, 1, 1, 0, 0, 0))
            entry.compress_type = zipfile.ZIP_DEFLATED
            entry.external_attr = 0o100644 << 16
            bundle.writestr(entry, content)
    return files


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT / 'benchmarks')
    parser.add_argument('--zip', type=Path, required=True, help='upload ZIP path outside the repository')
    args = parser.parse_args(argv)
    files = assemble(args.output, args.zip)
    print(f'{len(files)} files assembled; no models run')
    print('Dataset:', args.output.resolve())
    print('Upload ZIP:', args.zip.resolve())


if __name__ == '__main__':
    main()
