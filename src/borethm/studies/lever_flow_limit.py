"""Refine L8's bit-temperature boundary without claiming full tool survival."""
import json
from dataclasses import replace

from borethm.studies import levers as lv


def main(root=None):
    root = lv.require_path(root or lv.RESULTS, 'Flow-limit study evidence')
    for key in ('soultz', 'united-downs'):
        path = root / key / 'L8' / 'summary.json'
        summary = json.loads(path.read_text())
        valid = [r for r in summary['trials'] if r['metrics'] and r['metrics']['solver_ok']]
        passes = [r for r in valid if r['metrics']['tool_peaks_C']['drilling'] <= 200.]
        failures = [r for r in valid if r['metrics']['tool_peaks_C']['drilling'] > 200.]
        if not passes:
            summary['bit_flow_limit'] = dict(bracket=None,
                note='No bit-surviving flow among the evaluated flows at or below the base flow.')
        else:
            passing = min(passes, key=lambda r: r['settings']['flow_L_s'])
            lower = [r for r in failures if r['settings']['flow_L_s'] < passing['settings']['flow_L_s']]
            if not lower:
                raise ValueError('a lower failing flow is required')
            failing = max(lower, key=lambda r: r['settings']['flow_L_s'])
            def evaluate(flow):
                record = lv.trial(key, 'L8', replace(lv.base_settings(key), flow_L_s=flow), root=root)
                summary['trials'].append(record)
                if not record['metrics'] or not record['metrics']['solver_ok']:
                    raise ValueError('unresolved physical solve at the bit boundary')
                return record
            predicate = lambda r: r['metrics']['tool_peaks_C']['drilling'] <= 200.
            coarse = lv.bisect_minimum(evaluate,
                (failing['settings']['flow_L_s'], failing),
                (passing['settings']['flow_L_s'], passing), 0.5, predicate)
            failed = next(r for r in summary['trials'] if r['evidence'] == coarse['failing']['evidence'])
            fine = lv.bisect_minimum(evaluate,
                (coarse['failing']['intervention'], failed),
                (coarse['passing']['intervention'], coarse['minimum']), 0.25, predicate)
            summary['bit_flow_limit'] = dict(bracket=coarse, refined_bracket=fine,
                note='Bit-temperature boundary only. Run-in and all remaining site gates are assessed in each trial.')
        path.write_text(json.dumps(summary, indent=2) + '\n', encoding='utf-8', newline='\n')


if __name__ == '__main__':
    try:
        main()
    except ValueError as error:
        raise SystemExit(str(error)) from None
