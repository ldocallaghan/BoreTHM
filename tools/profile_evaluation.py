"""Profile installed site assessments without changing model functions.

Measure wall timings, stage/solve counts, function/water-property
statistics and peak resident memory. Requires Python 3.12+ for selective
sys.monitoring events. Package support for older Python is unaffected.

The observer uses internal site_evaluation stages (_stability, _ref_depth)
and the private water_props._props_cached statistics because no public
stage-timing API exists. It also checks _paths.repository_root to require
an installed wheel. No package function is replaced. Argument fingerprints
include callable defaults/closures and array bytes, but not module globals;
equal fingerprints do not prove that mutable results can safely be reused.

All child processes use the selected interpreter, one BLAS thread and an
external water-table cache. Profile shares are diagnostic; only separate
unprofiled CLI processes supply wall times. See docs/maintenance/performance.md.
"""
import argparse
from collections import defaultdict
import contextlib
import cProfile
import ctypes
import dataclasses
from datetime import datetime, timezone
import hashlib
from importlib.metadata import version
import inspect
import io
import json
import marshal
import os
from pathlib import Path
import platform
import pstats
import statistics
import struct
import subprocess
import sys
import time
import types

ROOT = Path(__file__).resolve().parents[1]
SITES = ('soultz', 'larderello', 'united-downs', 'pannonian', 'newberry')
THREADS = dict(OPENBLAS_NUM_THREADS='1', OMP_NUM_THREADS='1', MKL_NUM_THREADS='1')


def load_models():
    # Imports occur after child thread/cache settings have been selected.
    global np, PPoly, bt, se, m1, wall, tool, scalar_water
    import numpy as np
    from scipy.interpolate import PPoly
    import borethm as bt
    from borethm import site_evaluation as se, model1_coupled as m1
    from borethm import wall_thermal as wall, tool_thermal as tool
    from borethm import water_props as scalar_water
    from borethm._paths import repository_root
    if repository_root() is not None:
        raise RuntimeError('install a non-editable BoreTHM wheel in this interpreter before profiling')


def freeze(value, active=None):
    """Capture value state exactly; never invoke a supplied callable."""
    active = set() if active is None else active
    if value is None or type(value) in (bool, int, str):
        return [type(value).__name__, value]
    if isinstance(value, float):
        return [type(value).__name__, struct.pack('>d', value).hex()]
    if isinstance(value, np.generic):
        return ['numpy-scalar', value.dtype.str, value.tobytes().hex()]
    if isinstance(value, np.ndarray):
        if value.dtype.hasobject:
            raise TypeError('object arrays need a separate representation')
        return ['array', value.dtype.str, list(value.shape), hashlib.sha256(value.tobytes(order='C')).hexdigest()]
    identity = id(value)
    if identity in active:
        raise ValueError('cyclic solve input cannot be fingerprinted safely')
    active.add(identity)
    try:
        child = lambda item: freeze(item, active)
        kind = type(value).__module__ + '.' + type(value).__qualname__
        if isinstance(value, dict):
            return [kind, sorted([[child(k), child(v)] for k, v in value.items()], key=lambda x: json.dumps(x[0]))]
        if isinstance(value, (tuple, list)):
            return [kind, [child(v) for v in value]]
        if isinstance(value, types.FunctionType):
            return ['function', value.__module__, value.__qualname__,
                    hashlib.sha256(marshal.dumps(value.__code__)).hexdigest(),
                    child(value.__defaults__), child(value.__kwdefaults__),
                    [child(cell.cell_contents) for cell in (value.__closure__ or ())]]
        if isinstance(value, types.MethodType):
            return ['method', child(value.__func__), child(value.__self__)]
        if isinstance(value, PPoly):
            return [kind, child(value.c), child(value.x), child(value.axis), child(value.extrapolate)]
        if dataclasses.is_dataclass(value):
            return [kind, [[field.name, child(getattr(value, field.name))] for field in dataclasses.fields(value)]]
        if hasattr(value, '__dict__'):
            return [kind, child(vars(value))]
        raise TypeError('unsupported solve argument: ' + kind)
    finally:
        active.remove(identity)


class Observer:
    def __init__(self):
        self.codes = {}
        self.stack = []
        self.exclusive = defaultdict(int)
        self.inclusive = defaultdict(lambda: dict(calls=0, nanoseconds=0))
        self.observer_ns = 0
        self.last = None
        self.solve_calls = []
        self.solve_signature = inspect.signature(m1.solve)
        self.argument_names = tuple(self.solve_signature.parameters)
        self.tool_id = 3
        self.register('fluid_iteration', se.drilling_fluid)
        self.register('pipe_flow_selection', se.choose_circulation, se.flow_for_go)
        self.register('circulation_solves', m1.solve)
        self.register('wall_temperature', wall.run, wall.cooling_shape, wall.cylinder_recovery, wall.line_source_recovery)
        self.register('stability', se.stability_inputs, se._stability, se._ref_depth)
        self.register('connection_trip_cycle', se.site_cycle, se.trip_temperatures, se.pause_temperatures, se.trip_profile)
        self.register('whole_hole_windows', se.common_windows)
        self.register('equipment_checks', se.tool_gates, tool.run, tool.trip_in)
        self.register('report_json', se.report, se.export_result, se.result_dict, se.reading)

    @staticmethod
    def label(function):
        return function.__module__ + '.' + function.__qualname__

    def register(self, stage, *functions):
        for function in functions:
            function = inspect.unwrap(function)
            self.codes[function.__code__] = dict(stage=stage, label=self.label(function))

    def current_stage(self):
        for item in reversed(self.stack):
            if item['stage']:
                return item['stage']
        return 'other'

    def tick(self, now):
        if self.last is not None:
            self.exclusive[self.current_stage()] += now - self.last

    def start(self, code, offset):
        now = time.perf_counter_ns()
        self.tick(now)
        item = dict(self.codes[code], code=code, start=now, observed_before=self.observer_ns)
        if code is m1.solve.__code__:
            frame = sys._getframe(1)
            if frame.f_code is not code:
                raise RuntimeError('monitoring callback cannot inspect the solve frame')
            arguments = {key: frame.f_locals[key] for key in self.argument_names}
            frozen = freeze(arguments)
            encoded = json.dumps(frozen, separators=(',', ':'), ensure_ascii=True)
            item['solve_index'] = len(self.solve_calls)
            self.solve_calls.append(dict(index=item['solve_index'],
                signature=hashlib.sha256(encoded.encode()).hexdigest(),
                arguments=frozen, parent_stage=self.current_stage()))
        self.stack.append(item)
        end = time.perf_counter_ns()
        self.observer_ns += end - now
        self.last = end

    def finish(self, code, offset, value):
        now = time.perf_counter_ns()
        self.tick(now)
        item = self.stack.pop()
        if item['code'] is not code:
            raise RuntimeError('stage entry and exit events do not match')
        inclusive = now - item['start'] - (self.observer_ns - item['observed_before'])
        total = self.inclusive[item['label']]
        total['calls'] += 1
        total['nanoseconds'] += inclusive
        if 'solve_index' in item:
            record = self.solve_calls[item['solve_index']]
            record.update(profiled_seconds=inclusive / 1e9,
                          success=bool(value['success']) if isinstance(value, dict) and 'success' in value else None)
            frame = sys._getframe(1)
            if frame.f_code is code:
                record['cache_hit'] = bool(frame.f_locals.get('_cache_hit', False))
        end = time.perf_counter_ns()
        self.observer_ns += end - now
        self.last = end

    def unwind(self, code, offset, error):
        if code in self.codes:
            self.finish(code, offset, None)

    def enable(self):
        monitoring = sys.monitoring
        monitoring.use_tool_id(self.tool_id, 'evaluation-observer')
        monitoring.register_callback(self.tool_id, monitoring.events.PY_START, self.start)
        monitoring.register_callback(self.tool_id, monitoring.events.PY_RETURN, self.finish)
        monitoring.register_callback(self.tool_id, monitoring.events.PY_UNWIND, self.unwind)
        monitoring.set_events(self.tool_id, monitoring.events.PY_UNWIND)
        for code in self.codes:
            monitoring.set_local_events(self.tool_id, code, monitoring.events.PY_START | monitoring.events.PY_RETURN)
        self.last = time.perf_counter_ns()

    def disable(self):
        now = time.perf_counter_ns()
        self.tick(now)
        monitoring = sys.monitoring
        monitoring.set_events(self.tool_id, 0)
        for code in self.codes:
            monitoring.set_local_events(self.tool_id, code, 0)
        for event in (monitoring.events.PY_START, monitoring.events.PY_RETURN, monitoring.events.PY_UNWIND):
            monitoring.register_callback(self.tool_id, event, None)
        monitoring.free_tool_id(self.tool_id)
        if self.stack:
            raise RuntimeError('stage events left an unfinished call')

    def result(self):
        total = sum(self.exclusive.values()) / 1e9
        seen = {}
        duplicates = []
        for record in self.solve_calls:
            signature = record['signature']
            if signature in seen:
                record['repeats_call'] = seen[signature]
                duplicates.append(record)
            else:
                seen[signature] = record['index']
        return dict(accounted_seconds=total, observer_seconds=self.observer_ns / 1e9,
            stages={key: dict(seconds=value / 1e9, percent=100 * value / 1e9 / total) for key, value in self.exclusive.items()},
            functions={key: dict(calls=value['calls'], inclusive_seconds=value['nanoseconds'] / 1e9) for key, value in self.inclusive.items()},
            solve_calls=len(self.solve_calls), repeated_calls=len(duplicates), unique_calls=len(seen),
            cache_hits=sum(record.get('cache_hit', False) for record in self.solve_calls),
            computed_solves=sum(not record.get('cache_hit', False) for record in self.solve_calls),
            repeated_profiled_solve_seconds=sum(r['profiled_seconds'] for r in duplicates),
            duplicate_definition='All bound parameters, exact float/array bytes, callable code/defaults/closure values, and object state at entry. No callable is invoked by the observer. Module globals are not included; matching arguments alone do not establish safe result reuse.',
            calls=self.solve_calls)


def function_rows(stats, field):
    rows = []
    for key, values in stats.stats.items():
        cc, nc, own, cumulative, callers = values
        rows.append(dict(file=key[0], line=key[1], function=key[2], primitive_calls=cc,
                         calls=nc, own_seconds=own, cumulative_seconds=cumulative))
    return sorted(rows, key=lambda row: row[field], reverse=True)


def table_lookup_accounting(stats):
    """Union of wrapper timings and direct interpolator caller-edge timings.

    props and cp do not call each other in the pinned baseline. Their
    interpolator children are excluded from the direct-call contribution.
    """
    wrappers = 0.0
    direct = 0.0
    edges = []
    for key, values in stats.stats.items():
        path = key[0].replace('\\', '/')
        if path.endswith('/borethm/water_table.py') and key[2] in ('props', 'cp'):
            wrappers += values[3]
        if path.endswith('/scipy/interpolate/_rgi.py') and key[2] == '__call__':
            for caller, detail in values[4].items():
                wrapped = caller[0].replace('\\', '/').endswith('/borethm/water_table.py')
                edges.append(dict(file=caller[0], line=caller[1], function=caller[2],
                                  calls=detail[1], cumulative_seconds=detail[3], inside_wrapper=wrapped))
                if not wrapped:
                    direct += detail[3]
    return dict(union_seconds=wrappers + direct, wrapper_inclusive_seconds=wrappers,
                direct_interpolator_seconds=direct, interpolator_caller_edges=edges,
                method='props + cp cumulative time, plus interpolator caller-edge cumulative time from outside water_table; wrapper children excluded')


def peak_memory():
    """OS-maintained resident peak of this fresh worker process, in bytes."""
    if sys.platform == 'win32':
        from ctypes import wintypes
        class Counters(ctypes.Structure):
            _fields_ = [('cb', wintypes.DWORD), ('PageFaultCount', wintypes.DWORD),
                ('PeakWorkingSetSize', ctypes.c_size_t), ('WorkingSetSize', ctypes.c_size_t),
                ('QuotaPeakPagedPoolUsage', ctypes.c_size_t), ('QuotaPagedPoolUsage', ctypes.c_size_t),
                ('QuotaPeakNonPagedPoolUsage', ctypes.c_size_t), ('QuotaNonPagedPoolUsage', ctypes.c_size_t),
                ('PagefileUsage', ctypes.c_size_t), ('PeakPagefileUsage', ctypes.c_size_t)]
        counters = Counters()
        counters.cb = ctypes.sizeof(counters)
        kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        kernel.GetCurrentProcess.restype = wintypes.HANDLE
        psapi = ctypes.WinDLL('psapi', use_last_error=True)
        psapi.GetProcessMemoryInfo.argtypes = (wintypes.HANDLE, ctypes.POINTER(Counters), wintypes.DWORD)
        if not psapi.GetProcessMemoryInfo(kernel.GetCurrentProcess(), ctypes.byref(counters), counters.cb):
            raise ctypes.WinError(ctypes.get_last_error())
        return dict(peak_resident_bytes=counters.PeakWorkingSetSize,
            resident_bytes=counters.WorkingSetSize, method='GetProcessMemoryInfo PeakWorkingSetSize')
    if sys.platform.startswith('linux') or sys.platform == 'darwin':
        import resource
        size = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        return dict(peak_resident_bytes=int(size if sys.platform == 'darwin' else size*1024),
                    method='getrusage(RUSAGE_SELF).ru_maxrss; OS-maintained lifetime resident peak')
    return dict(peak_resident_bytes=None, method='unsupported platform; no resident peak available')


def write_json(path, value):
    temporary = path.with_suffix(path.suffix+'.tmp')
    temporary.write_text(json.dumps(value, indent=2)+'\n', encoding='utf-8')
    temporary.replace(path)


def worker(mode, site, output):
    load_models()
    before = scalar_water._props_cached.cache_info()._asdict()
    memory_before = peak_memory() if mode == 'memory' else None
    observer = Observer() if mode == 'profile' else None
    profiler = cProfile.Profile() if observer is not None else None
    started = time.perf_counter()
    if observer is not None:
        observer.enable()
        profiler.enable()
    try:
        se.main(['--site', site, '--json', str(output/'result.json')])
    finally:
        if observer is not None:
            profiler.disable()
            observer.disable()
    result = dict(site=site, measured_seconds=time.perf_counter()-started,
        profile_scope='site_evaluation.main after imports/setup, including validation, report and JSON',
        scalar_water_cache_before=before,
        scalar_water_cache_after=scalar_water._props_cached.cache_info()._asdict())
    if mode == 'memory':
        result.update(memory=peak_memory(), memory_before_evaluation=memory_before)
    else:
        profiler.dump_stats(str(output/'evaluation.prof'))
        stats = pstats.Stats(profiler)
        rows = function_rows(stats, 'own_seconds')
        module = lambda name: [r for r in rows if name in r['file'].replace('\\', '/')]
        result['observation'] = observer.result()
        result['water'] = dict(
            scalar_water_calls=sum(r['calls'] for r in module('/borethm/water_props.py') if r['function']=='water'),
            iapws_own_seconds=sum(r['own_seconds'] for r in module('/iapws/')),
            iapws_calls=sum(r['calls'] for r in module('/iapws/')),
            table_lookup_accounting=table_lookup_accounting(stats),
            table_functions=module('/borethm/water_table.py'),
            interpolator_functions=[r for r in module('/scipy/interpolate/_rgi.py') if r['function']=='__call__'])
        solve_count = sum(r['calls'] for r in module('/borethm/model1_coupled.py') if r['function']=='solve')
        if solve_count != result['observation']['solve_calls']:
            raise RuntimeError('observer and cProfile circulation-solve counts differ')
        result['cprofile_solve_calls'] = solve_count
        result['top_25_own'] = rows[:25]
        result['top_25_cumulative'] = function_rows(stats, 'cumulative_seconds')[:25]
        write_json(output/'all-functions.json', rows)
        for order in ('tottime', 'cumtime'):
            with (output/f'top-{order}.txt').open('w', encoding='utf-8') as handle:
                pstats.Stats(profiler, stream=handle).sort_stats(order).print_stats(25)
    write_json(output/'measurement.json', result)


def protected_hashes():
    paths = subprocess.check_output(['git', '-C', str(ROOT), 'ls-files', '-z', '--',
        'src/borethm', 'results', 'tests/golden', 'benchmarks']).decode('utf-8').split('\0')
    return {name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in paths if name}


def environment_record():
    load_models()
    config = io.StringIO()
    with contextlib.redirect_stdout(config):
        np.show_config()
    try:
        from threadpoolctl import threadpool_info
        blas = threadpool_info()
    except ImportError:
        blas = None
    cpu = platform.processor()
    if sys.platform == 'win32':
        import winreg
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                r'HARDWARE\DESCRIPTION\System\CentralProcessor\0') as key:
            cpu = winreg.QueryValueEx(key, 'ProcessorNameString')[0].strip()
    return dict(python=sys.version, executable=sys.executable, platform=platform.platform(),
        cpu=cpu, logical_processors=os.cpu_count(), package=str(Path(bt.__file__).resolve()),
        packages={name:version(name) for name in ('borethm', 'numpy', 'scipy', 'iapws')},
        thread_environment={name:os.environ.get(name) for name in THREADS},
        blas_runtime=blas, numpy_configuration=config.getvalue(),
        git_commit=subprocess.check_output(['git','-C',str(ROOT),'rev-parse','HEAD'],text=True).strip(),
        git_status=subprocess.check_output(['git','-C',str(ROOT),'status','--porcelain'],text=True))


def summary_document(state):
    lines = ['# Evaluation profile summary', '',
        'Wall times use fresh unprofiled CLI processes with a warm disk cache.',
        'Profiles exclude imports/setup and supply diagnostic shares and counts.',
        'Memory is measured separately for the selected site with the largest median.', '',
        '| Site | Runs | Median wall (s) | Range (s) | Requests | Cached | Computed | Repeated inputs | Peak RSS (MiB) |',
        '|---|---:|---:|---:|---:|---:|---:|---:|---:|']
    memory = state.get('memory', {})
    for site, item in state['sites'].items():
        observation = item.get('profile', {}).get('observation', {})
        peak = memory.get('peak_resident_bytes') if memory.get('site') == site else None
        lines.append(f"| {site} | {len(item['wall_seconds'])} | {item['median_seconds']:.3f} | "
            f"{min(item['wall_seconds']):.3f}–{max(item['wall_seconds']):.3f} | "
            f"{observation.get('solve_calls','')} | {observation.get('cache_hits','')} | "
            f"{observation.get('computed_solves','')} | {observation.get('repeated_calls','')} | "
            f"{peak/1048576 if peak is not None else ''} |")
    lines += ['', '| Stage | '+' | '.join(state['sites'])+' |',
              '|---|'+'---:|'*len(state['sites'])]
    stages = sorted({stage for item in state['sites'].values()
        for stage in item.get('profile', {}).get('observation', {}).get('stages', {})})
    for stage in stages:
        values = [item.get('profile', {}).get('observation', {}).get('stages', {}).get(stage, {}).get('percent',0)
                  for item in state['sites'].values()]
        lines.append('| '+stage+' | '+' | '.join(f'{value:.2f}%' for value in values)+' |')
    lines += ['', '| Site | Scalar water calls | LRU hits/misses/size | IAPWS own (s) | Lookup union (s) |',
              '|---|---:|---|---:|---:|']
    for site,item in state['sites'].items():
        if 'profile' not in item:
            continue
        record=item['profile']
        cache=record['scalar_water_cache_after']
        water=record['water']
        lines.append(f"| {site} | {water['scalar_water_calls']} | "
            f"{cache['hits']}/{cache['misses']}/{cache['currsize']} | "
            f"{water['iapws_own_seconds']:.6f} | {water['table_lookup_accounting']['union_seconds']:.3f} |")
    lines += ['', 'Lookup time overlaps stage time. Repeated-call cost is an upper bound on reuse savings.',
              'Module globals are outside argument fingerprints; mutable results require independent copies.',
              '', '## Files', '',
              '- `summary.json`: commands, timings, environment and equality checks.',
              '- `timings/`: every unprofiled export.',
              '- `profiles/SITE/`: result, measurement, raw cProfile, all functions and both top-25 lists.',
              '- `memory/SITE/`: separate unprofiled result and OS-maintained resident peak.',
              '- `protected-files.json`: source and evidence hashes before the run.',
              '- `logs/`: complete child-process output.', '']
    return '\n'.join(lines)


def run_measurements(args):
    output = args.output.resolve()
    cache = args.cache_dir.resolve() if args.cache_dir else output/'cache'
    for path in (output, cache):
        if path.is_relative_to(ROOT):
            raise ValueError('output and cache directories must be outside the checkout')
    if output.exists() and (not output.is_dir() or any(output.iterdir())):
        raise ValueError('output must be a new or empty directory')
    os.environ.update(THREADS)
    os.environ['BORETHM_CACHE_DIR'] = str(cache)
    os.environ.pop('PYTHONPATH', None)
    os.environ.pop('PYTHONHOME', None)
    environment = environment_record()
    package = Path(environment['package']).parent
    if output.is_relative_to(package) or cache.is_relative_to(package):
        raise ValueError('output and cache directories must be outside the installed package')
    before = protected_hashes()
    output.mkdir(parents=True, exist_ok=True)
    cache.mkdir(parents=True, exist_ok=True)
    for name in ('logs','timings','profiles','memory'):
        (output/name).mkdir()
    write_json(output/'protected-files.json', before)
    state = dict(status='running', started_utc=datetime.now(timezone.utc).isoformat(),
        environment=environment, output=str(output), cache=str(cache), repeats=args.repeats,
        runs=[], sites={}, excluded_result_fields=[])
    def persist():
        write_json(output/'summary.json',state)
        (output/'summary.md').write_text(summary_document(state),encoding='utf-8')
    def run(label, command):
        log = output/'logs'/f'{label}.log'
        print('START',label,flush=True)
        started=time.perf_counter()
        with log.open('w',encoding='utf-8') as stream:
            process=subprocess.Popen(command,cwd=output,stdout=stream,stderr=subprocess.STDOUT)
            try:
                while True:
                    try:
                        code=process.wait(timeout=45)
                        break
                    except subprocess.TimeoutExpired:
                        print('RUNNING',label,f'{time.perf_counter()-started:.0f}s',flush=True)
            except BaseException:
                process.terminate()
                process.wait()
                raise
        state['runs'].append(dict(label=label,command=[str(x) for x in command],cwd=str(output),
            wall_seconds=time.perf_counter()-started,returncode=code,log=str(log)))
        persist()
        if code:
            raise RuntimeError(f'{label} failed with exit {code}; see {log}')
        print('DONE',label,f"{state['runs'][-1]['wall_seconds']:.3f}s",flush=True)
        return state['runs'][-1]['wall_seconds']
    def same_result(site, path):
        reference=state['sites'][site]['reference']
        actual=json.loads(path.read_text(encoding='utf-8'))
        if actual != json.loads(Path(reference).read_text(encoding='utf-8')):
            raise RuntimeError(f'{site}: exported JSON differs from the unprofiled reference: {path}')
    persist()
    try:
        run('warm-cache',[sys.executable,'-u','-X','utf8','-m','borethm.water_table'])
        state['warm_cache']=[dict(name=path.name,bytes=path.stat().st_size,
            sha256=hashlib.sha256(path.read_bytes()).hexdigest()) for path in sorted(cache.glob('*.npz'))]
        scripts=Path(sys.executable).parent
        cli=scripts/('borethm-evaluate.exe' if os.name=='nt' else 'borethm-evaluate')
        if not cli.is_file():
            raise RuntimeError(f'installed CLI not found: {cli}')
        for repeat in range(1,args.repeats+1):
            order=args.sites if repeat%2 else list(reversed(args.sites))
            for site in order:
                destination=output/'timings'/f'{site}-{repeat}.json'
                seconds=run(f'{site}-wall-{repeat}',[str(cli),'--site',site,'--json',str(destination)])
                item=state['sites'].setdefault(site,dict(wall_seconds=[],reference=str(destination)))
                item['wall_seconds'].append(seconds)
                item['median_seconds']=statistics.median(item['wall_seconds'])
                same_result(site,destination)
                persist()
        for site in args.sites:
            destination=output/'profiles'/site
            destination.mkdir()
            run(f'{site}-profile',[sys.executable,'-u','-X','utf8',str(Path(__file__).resolve()),
                '--_worker','profile','--sites',site,'--output',str(destination)])
            same_result(site,destination/'result.json')
            record=json.loads((destination/'measurement.json').read_text(encoding='utf-8'))
            record['result_equality']=dict(equal=True,excluded_fields=[])
            write_json(destination/'measurement.json',record)
            state['sites'][site]['profile']={key:value for key,value in record.items()
                if key not in ('top_25_own','top_25_cumulative','observation')}
            state['sites'][site]['profile']['observation']={key:value for key,value in record['observation'].items()
                if key!='calls'}
            persist()
        slowest=max(args.sites,key=lambda site:state['sites'][site]['median_seconds'])
        destination=output/'memory'/slowest
        destination.mkdir()
        run(f'{slowest}-memory',[sys.executable,'-u','-X','utf8',str(Path(__file__).resolve()),
            '--_worker','memory','--sites',slowest,'--output',str(destination)])
        same_result(slowest,destination/'result.json')
        record=json.loads((destination/'measurement.json').read_text(encoding='utf-8'))
        record['result_equality']=dict(equal=True,excluded_fields=[])
        write_json(destination/'measurement.json',record)
        state['memory']=dict(site=slowest,**record['memory'],result_equality=record['result_equality'])
        state['status']='completed'
    except BaseException as error:
        state.update(status='failed',error=str(error))
        raise
    finally:
        unchanged=protected_hashes()==before
        state.update(protected_files_unchanged=unchanged,completed_utc=datetime.now(timezone.utc).isoformat())
        if not unchanged:
            state.update(status='failed',error='protected source or evidence changed during the run')
        persist()
        if not unchanged:
            raise RuntimeError(state['error'])


def main():
    parser=argparse.ArgumentParser(description=__doc__,formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--sites',nargs='+',choices=SITES,default=list(SITES))
    parser.add_argument('--output',type=Path,required=True,help='new or empty directory outside the checkout')
    parser.add_argument('--cache-dir',type=Path,help='external water cache; default: OUTPUT/cache')
    parser.add_argument('--repeats',type=int,default=3,help='fresh unprofiled runs per site (default: 3)')
    parser.add_argument('--_worker',choices=['profile','memory'],help=argparse.SUPPRESS)
    args=parser.parse_args()
    if sys.version_info < (3,12):
        parser.error('this maintenance profiler requires Python 3.12+ for sys.monitoring')
    if args.repeats < 1 or len(set(args.sites)) != len(args.sites):
        parser.error('repeats must be positive and sites must not repeat')
    if args._worker:
        if len(args.sites)!=1:
            parser.error('a worker requires exactly one site')
        worker(args._worker,args.sites[0],args.output.resolve())
    else:
        try:
            run_measurements(args)
        except (RuntimeError,ValueError) as error:
            parser.exit(1,f'{error}\n')


if __name__ == '__main__':
    main()
