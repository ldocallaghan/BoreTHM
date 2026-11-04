"""Write reader-facing tapered-joint results from the compact tables."""
import csv
import hashlib
import json
from pathlib import Path
import re

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
OUT=HERE/'results'
TAPERED=('tapered_primary','tapered_long','tapered_steep','tapered_pin_length')
ALL=('working','installed_primary','installed_no_local',*TAPERED)
LABEL=dict(working='Working',installed_primary='`installed_primary` (abrupt)',installed_no_local='`installed_no_local`',
    tapered_primary='`tapered_primary`, 11.5°',tapered_long='`tapered_long`, 6.3°',tapered_steep='`tapered_steep`, 30°',
    tapered_pin_length='`tapered_pin_length`, 11.5°')
GROUPS=(('17','500'),('19','600'),('20','600'),('27','400'),('27','600'),('38','600'))


def read(path):
    with path.open(encoding='utf-8',newline='') as f:return list(csv.DictReader(f))


def table(headers,rows):
    return '\n'.join(['| '+' | '.join(headers)+' |','| '+' | '.join(['---']*len(headers))+' |']+['| '+' | '.join(map(str,r))+' |' for r in rows])


def declared_scores():
    """Read the expected G5 and G6 scores from the committed declaration table."""
    found={}
    for line in (HERE/'README.md').read_text(encoding='utf-8').splitlines():
        m=re.match(r'\| (tapered_\w+) \| [\d.]+–[\d.]+ \| ([-+\d.]+) \| ([-+\d.]+) \| ([-+\d.]+) \|$',line)
        if m:found[m[1]]=tuple(float(m[i]) for i in (2,3,4))
    assert set(found)=={'tapered_primary','tapered_long','tapered_steep'}
    return found


class Tables:
    def __init__(self):
        self.summary={r['candidate']:r for r in read(OUT/'summary.csv')}
        self.comparison=read(OUT/'comparison.csv')
        self.slopes=read(OUT/'secondary/slopes.csv')
        self.shallow=read(OUT/'shallow-diagnostic.csv')
        self.decision=json.loads((OUT/'decision.json').read_text(encoding='utf-8'))
        assert self.decision['recommendation'].startswith('recommend tapered_primary')
        self.checks=read(OUT/'prediction-checks.csv')
        self.tripchecks=read(OUT/'secondary/prediction-checks.csv')

    def value(self,v,key):return float(self.summary[v][key])

    def bias(self,v,gap,well,group):
        return next(r['candidate_bias'] for r in self.comparison if (r['candidate'],r['gap'],r['well'],r['group'])==(v,gap,well,group))

    def slope(self,v,group):
        return next(r for r in self.slopes if r['candidate']==v and (r['assembly'],r['flow_centre_gpm'])==group)

    def score_table(self):
        return table(['Calculation','G1 16A RMS, psi','G1 16B RMS, psi','G2 16A bias, kW','G2 16B bias, kW','G3 16A RMS, °C','G4 RMS, °C','G5 return bias, °C','G6 regular bias, °C','G6 trial bias, °C'],
            [[LABEL[v],*[f'{self.value(v,k):.2f}' for k in ('G1_16A_RMS_psi','G1_16B_RMS_psi','G2_16A_bias_kW','G2_16B_bias_kW','G3_16A_RMS_C','G4_peak_error_RMS_C','G5_16A_return_bias_C','G6_regular_bias_C','G6_trial_bias_C')]] for v in ALL])

    def g1_table(self,well):
        groups=[r['group'] for r in self.comparison if r['candidate']=='working' and r['gap']=='G1' and r['well']==well]
        return table(['Calculation',*[f'BHA {g}' for g in groups]],
            [[LABEL[v],*[f"{float(self.bias(v,'G1',well,g)):+.2f}" for g in groups]] for v in ALL])

    def ratio_table(self):
        return table(['Calculation',*[f"EOW {a}, {f} gpm"+(' (insulated)' if a=='19' else '') for a,f in GROUPS]],
            [[LABEL[v],*[f"{float(self.slope(v,g)['slope_ratio']):.2f}" for g in GROUPS]] for v in ALL])

    def fractions(self):
        rows={}
        for g in GROUPS:
            if g[0]=='19':continue
            s0=float(self.slope('installed_no_local',g)['modelled_slope']);sa=float(self.slope('installed_primary',g)['modelled_slope'])
            sm=float(self.slope('working',g)['measured_slope'])
            rows[g]=dict(measured=sm,bound=(sm-s0)/(sa-s0),ci=float(self.slope('working',g)['measured_ci95_half']),
                **{v:(float(self.slope(v,g)['modelled_slope'])-s0)/(sa-s0) for v in TAPERED},
                model=float(self.slope('tapered_primary',g)['modelled_slope']),model_ci=float(self.slope('tapered_primary',g)['modelled_ci95_half']))
        return rows

    def fraction_table(self):
        return table(['EOW, flow','Measured slope ± 95%','`tapered_primary` slope ± 95%','Entry 12 bound','`tapered_long`','`tapered_primary`','`tapered_pin_length`','`tapered_steep`'],
            [[f'{g[0]}, {g[1]} gpm',f"{r['measured']:.1f} ± {r['ci']:.1f}",f"{r['model']:.1f} ± {r['model_ci']:.1f}",f"{r['bound']:.3f}",*[f'{r[v]:.3f}' for v in ('tapered_long','tapered_primary','tapered_pin_length','tapered_steep')]] for g,r in self.fractions().items()])

    def forecast_table(self):
        rows=[]
        for v,(g5,reg,trial) in declared_scores().items():
            rows.append([LABEL[v],f'{g5:+.2f}',f"{self.value(v,'G5_16A_return_bias_C'):+.2f}",f'{reg:+.2f}',f"{self.value(v,'G6_regular_bias_C'):+.2f}",f'{trial:+.2f}',f"{self.value(v,'G6_trial_bias_C'):+.2f}"])
        return table(['Variant','G5 expected','G5 scored','G6 regular expected','G6 regular scored','G6 trial expected','G6 trial scored'],rows)

    def largest_forecast_difference(self):
        return max(abs(self.value(v,k)-x) for v,xs in declared_scores().items() for k,x in zip(('G5_16A_return_bias_C','G6_regular_bias_C','G6_trial_bias_C'),xs))

    def shallow_range(self,v='tapered_primary'):
        x=[float(r['candidate_deficit_psi']) for r in self.shallow if r['candidate']==v]
        return min(x),max(x)

    def findings(self,prefix):
        """The statements shared by the results page and the log, so that they cannot diverge."""
        f=self.fractions();bounds=[r['bound'] for r in f.values()];pf=[r['tapered_primary'] for r in f.values()];sf=[r['tapered_steep'] for r in f.values()]
        regular=[g for g in GROUPS if g[0]!='19']
        ratio=lambda v:[float(self.slope(v,g)['slope_ratio']) for g in regular]
        v=self.value;P='tapered_primary';A='installed_primary';N='installed_no_local';W='working'
        reg_share=(v(P,'G6_regular_bias_C')-v(N,'G6_regular_bias_C'))/(v(A,'G6_regular_bias_C')-v(N,'G6_regular_bias_C'))
        trial_share=(v(P,'G6_trial_bias_C')-v(N,'G6_trial_bias_C'))/(v(A,'G6_trial_bias_C')-v(N,'G6_trial_bias_C'))
        b16=[float(self.bias(P,'G1','16B',g)) for g in ('12','13','15','16')]
        low,high=self.shallow_range()
        names=lambda chosen:' and '.join(', '.join(chosen).rsplit(', ',1))
        meets=lambda r:abs(r['measured']-r['model'])<=r['ci']+r['model_ci']
        overlap=names([f'EOW {g[0]} at {g[1]} gpm' for g,r in f.items() if meets(r)])
        apart=names([f'EOW {g[0]} at {g[1]} gpm' for g,r in f.items() if not meets(r)])
        assert sum(not meets(r) for r in f.values())==2
        e12=[r for r in self.shallow if r['candidate']==P and r['assembly']=='12']
        worst=max(abs(float(r['difference'])/float(r['tolerance'])) for r in self.checks)
        return f"""**Calculated joint-loss fraction.** At the sourced angle of 11.5° the bore local loss of one ordinary joint is 20.1% of the abrupt value. On the five regular-pipe trip groups the modelled slope fraction of `tapered_primary`, which also includes the retained abrupt annulus loss, is {100*min(pf):.1f}–{100*max(pf):.1f}%. Entry 12's bound is {100*min(bounds):.1f}–{100*max(bounds):.1f}%, so the sourced angle lies below it on every group. The unsourced 30° sensitivity lies above it, at {100*min(sf):.1f}–{100*max(sf):.1f}%. Columns come from [secondary/slopes.csv]({prefix}secondary/slopes.csv); slopes are in psi per 1000 ft.

{self.fraction_table()}

**Calculated slope ratios.** Measured/modelled regular-pipe ratios are {min(ratio(P)):.2f}–{max(ratio(P)):.2f} under `tapered_primary`, against {min(ratio(A)):.2f}–{max(ratio(A)):.2f} under `installed_primary`, {min(ratio(N)):.2f}–{max(ratio(N)):.2f} under `installed_no_local` and {min(ratio(W)):.2f}–{max(ratio(W)):.2f} for working. A ratio above one means that the modelled rise with added pipe is smaller than measured. The measured and modelled 95% intervals in the table overlap on {overlap} and are separate on {apart}, so the shortfall is resolved on those two groups only. EOW 19 adds insulated pipe, retains EIS connections and moves little in every variant.

**Calculated G6 change.** Against `installed_primary`, `tapered_primary` changes the G6 regular-pipe bias by {v(P,'G6_regular_bias_C')-v(A,'G6_regular_bias_C'):+.2f} °C, from {v(A,'G6_regular_bias_C'):+.2f} to {v(P,'G6_regular_bias_C'):+.2f} °C, and the trial bias by {v(P,'G6_trial_bias_C')-v(A,'G6_trial_bias_C'):+.2f} °C, from {v(A,'G6_trial_bias_C'):+.2f} to {v(P,'G6_trial_bias_C'):+.2f} °C. Against working the changes are {v(P,'G6_regular_bias_C')-v(W,'G6_regular_bias_C'):+.2f} and {v(P,'G6_trial_bias_C')-v(W,'G6_trial_bias_C'):+.2f} °C. Of the G6 contrast between `installed_no_local` and `installed_primary`, {100*reg_share:.1f}% on regular pipe and {100*trial_share:.1f}% on trial pipe remains.

**Calculated pressure and power.** Against `installed_primary`, G1 assembly-bias RMS rises from {v(A,'G1_16A_RMS_psi'):.2f} to {v(P,'G1_16A_RMS_psi'):.2f} psi on 16A and from {v(A,'G1_16B_RMS_psi'):.2f} to {v(P,'G1_16B_RMS_psi'):.2f} psi on 16B. Against working it is {v(P,'G1_16A_RMS_psi')-v(W,'G1_16A_RMS_psi'):+.2f} psi on 16A and {v(P,'G1_16B_RMS_psi')-v(W,'G1_16B_RMS_psi'):+.2f} psi on 16B. G2 well biases are {v(P,'G2_16A_bias_kW'):.2f} and {v(P,'G2_16B_bias_kW'):.2f} kW, against {v(A,'G2_16A_bias_kW'):.2f} and {v(A,'G2_16B_bias_kW'):.2f} kW under `installed_primary` and {v(W,'G2_16A_bias_kW'):.2f} and {v(W,'G2_16B_bias_kW'):.2f} kW for working.

**Calculated near-surface gap.** All ten primary shallow 16B windows have identical geometry under every variant, and every pressure change is zero. The remaining deficit is {low:.2f}–{high:.2f} psi, about 188–481 psi, as in entry 12. The windows are in [shallow-diagnostic.csv]({prefix}shallow-diagnostic.csv), columns `candidate_deficit_psi`, `pressure_change_psi` and `geometry_identical`.

**Inferred pressure balance.** The four motorless 16B assemblies now read low by {min(-x for x in b16):.2f}–{max(-x for x in b16):.2f} psi at full depth, which is the same order as the near-surface gap. This is consistent with entry 12's finding that the abrupt per-length excess offset missing near-surface losses. It does not establish that those losses account for the full-depth deficit: only EOW 12 appears in both sets, at {min(float(r['candidate_deficit_psi']) for r in e12):.1f}–{max(float(r['candidate_deficit_psi']) for r in e12):.1f} psi in the shallow windows and {-float(self.bias(P,'G1','16B','12')):.1f} psi at full depth, at different depths and flows. The 16A deficits are larger, at {min(-float(self.bias(P,'G1','16A',g)) for g in ('18','23','30','34','35r1','35r2','38','39','42')):.2f}–{max(-float(self.bias(P,'G1','16A',g)) for g in ('18','23','30','34','35r1','35r2','38','39','42')):.2f} psi, and have no shallow comparison.

**Inferred slope shortfall.** The sourced angle and the coefficients as stated give a smaller central per-length rise than the measured slope on all five regular-pipe groups, so a conical treatment at this angle does not by itself reproduce the measured rise, although the intervals resolve the difference on only two groups. The 30° case is not a sourced alternative, and no angle is selected from the bracket that the 11.5° and 30° cases form. The curved published profile, the unsourced step from upset to tool-joint bore, the transfer of the angle to 16B and the application of the correlation to mud are all unresolved.

**Calculated reproduction, and what it tests.** Scored changes reproduce the model-only predictions in {sum(r['passed']=='True' for r in self.checks)}/{len(self.checks)} checks across the 22 declared windows, with the largest difference {worst:.1e} of its declared tolerance, in [prediction-checks.csv]({prefix}prediction-checks.csv). All {len(self.tripchecks)} modelled trip-slope checks pass in [secondary/prediction-checks.csv]({prefix}secondary/prediction-checks.csv). The model-only calculation and the score use the same solver on the same inputs, so these checks establish that the score applied the declared treatment; they are not a forecast of an independent result. The forecast that could differ is the interpolation of entry 12's scores given in the declaration, whose largest difference from the score is {self.largest_forecast_difference():.2f} °C.

{self.forecast_table()}
"""

    def recommendation(self):
        return f"""**Inferred recommendation under the declared rule.** Recommend `tapered_primary` as the joint treatment for the working calculation. The scored changes reproduce the model-only predictions within 1 psi, 0.1 °C and 0.1% of power, paired coverage is retained, and the angle lies within the formula branch to 45°. The rule applies whatever the direction of the score change, and the direction is mixed. Against `installed_primary`, G1, G2, G3 and G5 are worse and G6 is better. Against working, G1 and G2 are better on 16B, G1 and G2 are slightly worse on 16A, and G6 is slightly worse. The rule's reproduction test is a test of implementation, as stated above. Its range test is limited: no numerical Reynolds range is stated in the accessible sources, the Crane formulas were checked through secondary statements, and the angle is extended beyond the published bore span and transferred to 16B. Adoption of entry 12's geometry and of this treatment remains Liam's decision as maintainer. Package defaults and golden files are unchanged."""


def main():
    t=Tables()
    states={v:json.loads((OUT/v/'manifest.json').read_text(encoding='utf-8')) for v in ('working',*TAPERED)}
    coverage=table(['Calculation','Circulation rows','Failed circulation','Failed available run-in','Originally unavailable run-in','Energy flags'],
        [[LABEL[v],s['circulation_rows'],len(s['circulation_failures']),len(s['run_in_failures']),len(s['run_in_originally_unavailable']),len(s['energy_flags'])] for v,s in states.items()])
    text=f'''# Tapered-joint comparison results

**Calculated comparisons.** All variants use the declared frozen samples and settings. Bias is model minus observation. Gap definitions follow entry 12. The tapered variants and the working copy were scored for this entry. `installed_primary` and `installed_no_local` are entry 12's archived [results](../../entry-12/results/README.md) and were not solved again.

## Six-gap results

**Calculated.** [summary.csv](summary.csv). [comparison.csv](comparison.csv) retains every gap, well and assembly or event group with its paired counts, and [sample-changes.csv](sample-changes.csv) and [assembly-changes.csv](assembly-changes.csv) give the changes by sample and assembly. The `_change` columns are against `installed_primary` and the `_vs_working` columns against working.

{t.score_table()}

## G1 by assembly

**Calculated biases, psi.** The field `candidate_bias` in [comparison.csv](comparison.csv), selected by `gap=G1` and `well`.

### 16B motorless assemblies

{t.g1_table('16B')}

### 16A

{t.g1_table('16A')}

## Secondary trip slopes

**Calculated measured/modelled ratios.** [secondary/slopes.csv](secondary/slopes.csv), column `slope_ratio`. Regular pipe is added on every group except EOW 19, which adds insulated pipe. These are secondary diagnostics and do not affect the recommendation.

{t.ratio_table()}

## Findings

{t.findings('')}
## Coverage

**Calculated.** Each variant retains all 467 circulation samples. The two originally unavailable run-in events, `23-off006` and `35r2-off008`, remain unavailable.

{coverage}

## Recommendation

{t.recommendation()} The full check list is in [decision.json](decision.json).

## Reproduction and storage

**Calculated archive.** Complete per-sample score outputs are external. [bulk-manifest.json](../bulk-manifest.json) records their hashes, sizes and rebuild commands, and the child manifests distinguish committed results from rebuildable files. Input and code hashes are recorded in the final [entry manifest](../manifest.json).
'''
    (OUT/'README.md').write_bytes(text.encode('utf-8'))
    p=HERE/'README.md';s=p.read_text(encoding='utf-8')
    if '## Scored comparison' not in s:
        s=s.rstrip('\n')+'\n\n## Scored comparison\n\n**Calculated.** The [results](results/README.md) report every gap and the secondary trip groups with paired coverage. The source choices and model-only predictions above remain unchanged. Rebuildable bulk outputs are external and identified by hashes in [bulk-manifest.json](bulk-manifest.json).\n'
        p.write_bytes(s.encode('utf-8'))
    log=ROOT/'docs/science/model-development.md';s=log.read_text(encoding='utf-8')
    marker='## 4 November 2026: entry 13, tapered drill-pipe joints'
    if marker in s:s=s.split(marker,1)[0].rstrip()+'\n'
    row='| Entry 13, tapered drill-pipe joints | Conical bore transitions at a published upset angle reduce the abrupt bore loss to 20.1% of its value, below the 29.7–44.8% bound of entry 12 | Frozen comparisons completed; declared predictions reproduced, and full-depth pressure and power errors increase against the abrupt treatment | Rule-based recommendation recorded; adoption pending; no package default changed |\n'
    if '| Entry 13, tapered' not in s:
        anchor=next(line for line in s.splitlines(True) if line.startswith('| Entry 12, installed ordinary drill pipe'))
        s=s.replace(anchor,anchor+row)
    prefix='../../validation/model-development/entry-13/'
    s+=f'''
{marker}

**Calculated change.** `HydraulicJoint` gains an optional conical treatment of the bore transitions of a connection, with the included angle as an argument. The default remains abrupt, and the annulus side keeps the abrupt treatment. [Entry 13]({prefix}README.md) declares four variants: `tapered_primary` at 11.5°, `tapered_long` at 6.3°, `tapered_steep` at 30° as an unsourced sensitivity, and `tapered_pin_length` at 11.5° with the restriction length set to the pin tong length. All other settings follow entry 12's `installed_primary`.

**Measured prior exposure.** The treatment was examined after the entry 12 scores, its slope ratios of 0.49–0.61 and 1.54–2.30, its joint-local-loss bound of 29.7–44.8%, and an informal mapping of that bound to about 13–20°, made during the review of entry 12, had been seen. **Calculated.** With the coefficients used here the bound corresponds to 17.0–25.8°. No angle or coefficient was chosen from these values or from G1, G2 or trip-slope agreement.

**Measured sources and limits.** The internal taper length of 3.838 in is from Tsukano et al. (1988), Figure 9, as quoted in EP0756682B1, and the upset bore of 3.500 in and transition length of 7.000 in are from Table I of that patent. The paper itself could not be accessed, and both sources describe curved transitions. The coefficients are those of Crane Technical Paper 410, A-26, checked against two secondary statements because the paper could not be accessed. The accessible statements give no numerical Reynolds range. **Inferred.** The published angle is extended beyond the published bore span and transferred to 16B. The [declaration]({prefix}README.md) gives the complete sources, values and limits.

**Calculated results.** [Entry 13 results]({prefix}results/README.md) compare all six gaps on the unchanged frozen samples, with `installed_primary` and `installed_no_local` taken from the entry 12 archive. Bias is model minus observation.

{t.score_table()}

**Calculated 16B G1 assembly biases, psi.**

{t.g1_table('16B')}

**Calculated measured/modelled trip-slope ratios.** EOW 19 adds insulated pipe.

{t.ratio_table()}

{t.findings(prefix+'results/')}
{t.recommendation()}
'''
    log.write_bytes(s.encode('utf-8'))
    files=[p for p in HERE.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p!=HERE/'manifest.json']
    (HERE/'manifest.json').write_bytes((json.dumps(dict(declaration_commit=t.decision['declaration_commit'],package_defaults_changed=False,adopted=False,
        files_sha256={p.relative_to(HERE).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(files)}),indent=2)+'\n').encode('utf-8'))
    print('Results, log entry and final manifest written.')


if __name__=='__main__':main()
