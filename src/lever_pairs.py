"""Try at most one C6 pair per site after the single-lever tables complete."""
import argparse
from dataclasses import asdict, replace
import hashlib
import json
from pathlib import Path

import levers as lv


def pressure_width(record):
    return min(record['metrics']['pressure_margin_SG'].values())


def select_pair(key, summaries):
    if any(record['assessment']['reopened'] for summary in summaries for record in summary['trials']):
        return []
    baseline = lv.base_settings(key)
    reference = next(record for summary in summaries for record in summary['trials']
                     if record['settings'] == asdict(baseline) and record['metrics'])
    base_margin = pressure_width(reference)
    ranked = []
    for summary in summaries:
        candidates = [record for record in summary['trials'] if record['metrics']
                      and record['settings'] != asdict(baseline)
                      and record['metrics']['solver_ok']
                      and record['result']['components']['window_refinement']['converged']
                      and (record['mpd'] is None or record['mpd']['ok'])]
        if candidates:
            best = max(candidates, key=pressure_width)
            ranked.append(dict(lever=summary['lever'], improvement_SG=pressure_width(best) - base_margin,
                               record=best))
    return sorted(ranked, key=lambda item: (-item['improvement_SG'], item['lever']))[:2]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sites', nargs='+', choices=['soultz', 'united-downs'], default=['soultz', 'united-downs'])
    args = parser.parse_args()
    for key in args.sites:
        summaries = [json.loads((lv.RESULTS / key / ('L' + str(i)) / 'summary.json').read_text())
                     for i in range(1, 9)]
        selected = select_pair(key, summaries)
        if not selected:
            print(key, 'a single lever reopened the site; no pair is required', flush=True)
            continue
        if len(selected) != 2:
            raise ValueError('two converged, applicable single-lever evaluations are needed for the pair')
        base = lv.base_settings(key)
        values = asdict(base)
        for item in selected:
            values.update({name: value for name, value in item['record']['settings'].items()
                           if value != asdict(base)[name]})
        label = 'PAIR-' + '-'.join(item['lever'] for item in selected)
        print(key, 'selected', label, [item['improvement_SG'] for item in selected], flush=True)
        combined = lv.trial(key, label, lv.Settings(**values))
        summary = dict(site=key, pair=[item['lever'] for item in selected],
            ranking='increase in the narrower common pressure-window width, surface SG; '
                    'converged and refined trials only, with achievable MPD control',
            selected=[dict(lever=item['lever'], improvement_SG=item['improvement_SG'],
                           evidence=item['record']['evidence']) for item in selected],
            trial=combined, driver_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
        destination = lv.RESULTS / key / label / 'summary.json'
        destination.write_text(json.dumps(summary, indent=2) + '\n', encoding='utf-8', newline='\n')


if __name__ == '__main__':
    main()
