"""Write reader-facing installed-pipe results from the final compact tables."""
import csv
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
VARIANTS=('working','installed_primary','installed_abrupt','installed_no_local','installed_premium','installed_steel')


def read(path):
    with path.open(encoding='utf-8',newline='') as f:return list(csv.DictReader(f))


def table(headers,rows):
    return '\n'.join(['| '+' | '.join(headers)+' |','| '+' | '.join(['---']*len(headers))+' |']+['| '+' | '.join(map(str,r))+' |' for r in rows])


def fmt(value):return 'unavailable' if value in ('',None) else f'{float(value):.2f}'


def joint_loss_interpretation(out, link_prefix='', heading_level=2):
    """Explain the archived pressure/temperature contrast without solving.

    The interpolation fraction is a diagnostic slope bound. It is never
    supplied to a model, and the two EOW 27 flow groups remain separate.
    """
    summaries={r['candidate']:r for r in read(out/'summary.csv')}
    working=summaries['working'];primary=summaries['installed_primary'];no_local=summaries['installed_no_local']
    pboard=read(out/'installed_primary/scoreboard.csv');wboard=read(out/'working/scoreboard.csv')
    pb={r['group']:float(r['bias']) for r in pboard if r['gap']=='G1' and r['well']=='16B'}
    wb={r['group']:float(r['bias']) for r in wboard if r['gap']=='G1' and r['well']=='16B'}
    pa={r['group']:float(r['bias']) for r in pboard if r['gap']=='G1' and r['well']=='16A'}
    bias_table=table(['16B assembly','Working bias, psi','Installed-primary bias, psi'],
        [[bha,f'{wb[bha]:+.2f}',f'{pb[bha]:+.2f}'] for bha in ('12','13','15','16')])
    shallow=read(out/'shallow-diagnostic.csv')
    low=min(float(r['installed_primary_deficit_psi']) for r in shallow)
    high=max(float(r['installed_primary_deficit_psi']) for r in shallow)
    depth_low=min(float(r['bit_depth_ft']) for r in shallow);depth_high=max(float(r['bit_depth_ft']) for r in shallow)
    slopes=read(out/'secondary/slopes.csv')
    def key(r):return r['well'],r['role'],r['assembly'],r['excursion'],r['flow_centre_gpm']
    ordinary=[r for r in slopes if r['candidate']=='installed_primary' and r['added_pipe']=='regular']
    without={key(r):r for r in slopes if r['candidate']=='installed_no_local' and r['added_pipe']=='regular'}
    assert len(ordinary)==len(without)==5
    fractions=[];p_ratios=[];n_ratios=[];bound_rows=[]
    for row in ordinary:
        other=without[key(row)]
        measured=float(row['measured_slope']);abrupt=float(row['modelled_slope']);base=float(other['modelled_slope'])
        assert abs(measured-float(other['measured_slope']))<1e-10
        fraction=(measured-base)/(abrupt-base)
        assert 0<fraction<1
        fractions.append(fraction);p_ratios.append(measured/abrupt);n_ratios.append(measured/base)
        bound_rows.append([row['assembly'],row['excursion'],row['flow_centre_gpm'],
            f'{measured:.3f}',f'{base:.3f}',f'{abrupt:.3f}',f'{fraction:.4f}'])
    bounds=table(['EOW','Excursion','Flow group, US gpm','Measured slope','No-local slope','Abrupt slope','Joint-local-loss fraction'],bound_rows)
    temperatures=table(['Calculation','G6 regular bias, °C','G6 trial bias, °C'],
        [[v,f"{float(summaries[v]['G6_regular_bias_C']):+.2f}",f"{float(summaries[v]['G6_trial_bias_C']):+.2f}"]
         for v in ('working','installed_primary','installed_no_local')])
    regular_increase=float(primary['G6_regular_bias_C'])-float(working['G6_regular_bias_C'])
    trial_increase=float(primary['G6_trial_bias_C'])-float(working['G6_trial_bias_C'])
    regular_local=float(primary['G6_regular_bias_C'])-float(no_local['G6_regular_bias_C'])
    trial_local=float(primary['G6_trial_bias_C'])-float(no_local['G6_trial_bias_C'])
    return f"""{'#'*heading_level} Pressure compensation and joint-loss bound

**Calculated:** [Installed-primary scoreboard]({link_prefix}installed_primary/scoreboard.csv) and [working scoreboard]({link_prefix}working/scoreboard.csv), selected by `gap=G1`, `well=16B` and `group`, give the motorless assembly biases below. Bias is model minus measured pressure. Working biases span {min(wb.values()):+.2f} to {max(wb.values()):+.2f} psi; installed-primary biases span {min(pb.values()):+.2f} to {max(pb.values()):+.2f} psi.

{bias_table}

**Calculated:** The installed-primary 16A assembly biases span {min(pa.values()):+.2f} to {max(pa.values()):+.2f} psi in the same scoreboard, selected by `well=16A`. BHA 38 is {pa['38']:+.2f} psi and BHA 39 is {pa['39']:+.2f} psi.

**Calculated:** [shallow-diagnostic.csv]({link_prefix}shallow-diagnostic.csv), columns `bit_depth_ft`, `installed_primary_deficit_psi` and `pressure_change_psi`, gives ten shallow 16B windows at {depth_low:.2f}–{depth_high:.2f} ft. Their partial strings contain no ordinary pipe, and every installed correction is zero. The model still reads low by {low:.2f}–{high:.2f} psi, about 188–481 psi. The four full-depth motorless assembly means now read high by {min(pb.values()):.2f}–{max(pb.values()):.2f} psi.

**Calculated:** In [secondary/slopes.csv]({link_prefix}secondary/slopes.csv), regular-pipe measured/modelled slope ratios span {min(p_ratios):.4f}–{max(p_ratios):.4f} under `installed_primary`, about 0.49–0.61, and {min(n_ratios):.4f}–{max(n_ratios):.4f} under `installed_no_local`, about 1.54–2.30. Thus the abrupt modelled rise is {min(1/r for r in p_ratios):.2f}–{max(1/r for r in p_ratios):.2f} times the measured rise; the no-local rise is {min(1/r for r in n_ratios):.2f}–{max(1/r for r in n_ratios):.2f} times measured. The measured rise lies between them. All five flow groups across four assemblies are retained, including both EOW 27 flow groups.

**Inferred:** The shallow pressure shortfall, positive full-depth biases and excessive per-length rise together indicate that the abrupt joint treatment with the installed 3.0-in bore overstates the loss added with ordinary pipe on 16B. This excess per-length pressure offsets missing near-surface tool and surface losses at full depth. The G1 RMS reduction from {float(working['G1_16B_RMS_psi']):.2f} to {float(primary['G1_16B_RMS_psi']):.2f} psi therefore includes compensation between two errors. Improved full-depth G1 does not establish that the abrupt treatment is physically appropriate.

**Calculated bound, never an input:** Approximate each modelled slope as a body-friction baseline plus joint local loss. Use the no-local slope `S_0` as that baseline, the abrupt slope `S_a`, and the unchanged measured slope `S_m`. The fraction `f = (S_m - S_0)/(S_a - S_0)` gives the joint-local-loss share that would match the measured slope under this approximation. All slope columns below are psi per 1000 ft.

{bounds}

The fractions span {min(fractions):.4f}–{max(fractions):.4f}, or {100*min(fractions):.1f}–{100*max(fractions):.1f}% of the abrupt contribution. This assumes additive slopes and the same trip groups with their fixed temperature treatment. Other modelled contributions, including distributed restriction friction, are absorbed into the no-local baseline. It is a diagnostic bound, without a measured loss coefficient. It selects no treatment and supplies no model input.

**Calculated:** [summary.csv]({link_prefix}summary.csv), columns `G6_regular_bias_C` and `G6_trial_bias_C`, gives:

{temperatures}

Primary warms the regular and trial comparisons by {regular_increase:.2f} and {trial_increase:.2f} °C relative to working. Its contrast with the same installed geometry without joint local losses is {regular_local:.2f} and {trial_local:.2f} °C, respectively. The no-local biases remain close to working.

**Inferred:** Nearly all of the extra G6 warming is associated with the joint-local-loss term and its dissipation in this calculation. If the abrupt joint loss is overstated, that additional warming is overstated with it. This concerns the increment from the connection treatment; the earlier temperature biases remain unresolved.

**Inferred source gap:** A sourced transition treatment requires the installed pipe's internal upset diameter and taper length at the weld neck, and the bore length through the made-up tool joint, from the drill-pipe data sheets or manufacturer drawings. No taper angle or loss coefficient is selected from these bounds.
"""


def main():
    out=HERE/'results';summaries=read(out/'summary.csv');comparison=read(out/'comparison.csv')
    fh=next(r for r in read(HERE.parent/'entry-10/results/summary.csv') if r['candidate']=='fh')
    order=[next(r for r in summaries if r['candidate']==v) for v in VARIANTS]+[{**fh,'candidate':'entry10_fh'}]
    pressure=table(['Calculation','G1 16A RMS, psi','G1 16B RMS, psi','G2 16A bias, kW','G2 16B bias, kW'],
        [[r['candidate'],*[fmt(r[k]) for k in ('G1_16A_RMS_psi','G1_16B_RMS_psi','G2_16A_bias_kW','G2_16B_bias_kW')]] for r in order])
    thermal=table(['Calculation','G3 16A bias RMS, °C','G4 peak-error RMS, °C','G5 return bias, °C','G6 regular bias, °C','G6 trial bias, °C'],
        [[r['candidate'],*[fmt(r[k]) for k in ('G3_16A_RMS_C','G4_peak_error_RMS_C','G5_16A_return_bias_C','G6_regular_bias_C','G6_trial_bias_C')]] for r in order])
    boards={v:read(out/v/'scoreboard.csv') for v in VARIANTS}
    boards['entry10_fh']=read(HERE.parent/'entry-10/results/fh/scoreboard.csv')
    def bias(v,well,bha):return next(r['bias'] for r in boards[v] if (r['gap'],r['well'],r['group'])==('G1',well,bha))
    assembly_tables=[]
    for well in ('16A','16B'):
        bhas=[r['group'] for r in boards['working'] if r['gap']=='G1' and r['well']==well]
        assembly_tables.append('### '+well+' G1 assembly biases\n\n'+table(['Assembly','Working','Entry 10 FH','Primary/abrupt','No local','Premium','Steel'],
            [[bha,*[fmt(bias(v,well,bha)) for v in ('working','entry10_fh','installed_primary','installed_no_local','installed_premium','installed_steel')]] for bha in bhas]))
    trip=read(out/'secondary/slopes.csv');oldtrip=[r for r in read(HERE.parent/'entry-10/results/secondary/slopes.csv') if r['candidate']=='fh']
    keys=[(r['assembly'],r['excursion'],r['flow_centre_gpm']) for r in trip if r['candidate']=='working']
    def ratio(v,key):return next(r['slope_ratio'] for r in trip if r['candidate']==v and (r['assembly'],r['excursion'],r['flow_centre_gpm'])==key)
    triptable=table(['EOW / added pipe','Excursion','Flow, US gpm','Working','Entry 10 FH','Primary/abrupt','No local','Premium','Steel'],
        [[key[0]+(' / insulated' if key[0]=='19' else ' / ordinary'),key[1],key[2],fmt(ratio('working',key)),
          fmt(next(r['slope_ratio'] for r in oldtrip if (r['assembly'],r['excursion'],r['flow_centre_gpm'])==key)),
          *[fmt(ratio(v,key)) for v in ('installed_primary','installed_no_local','installed_premium','installed_steel')]] for key in keys])
    checks=read(out/'prediction-checks.csv');tripchecks=read(out/'secondary/prediction-checks.csv')
    shallow=read(out/'shallow-diagnostic.csv');shallow_min=min(float(r['installed_primary_deficit_psi']) for r in shallow);shallow_max=max(float(r['installed_primary_deficit_psi']) for r in shallow)
    shallow_table=table(['Window','EOW','Bit depth, ft','Measured pressure, psi','Working/primary pressure, psi','Remaining deficit, psi','Installed change, psi'],[[r['window_id'],r['assembly'],fmt(r['bit_depth_ft']),fmt(r['measured_spp_psi']),fmt(r['installed_primary_spp_psi']),fmt(r['installed_primary_deficit_psi']),fmt(r['pressure_change_psi'])] for r in shallow])
    decision=json.loads((out/'decision.json').read_text(encoding='utf-8'))
    states={v:json.loads((out/v/'manifest.json').read_text(encoding='utf-8')) for v in VARIANTS}
    failtable=table(['Calculation','Circulation rows','Failed circulation','Failed available run-in','Originally unavailable run-in','Energy flags'],
        [[v,states[v]['circulation_rows'],len(states[v]['circulation_failures']),len(states[v]['run_in_failures']),len(states[v]['run_in_originally_unavailable']),len(states[v]['energy_flags'])] for v in VARIANTS])
    working=next(r for r in summaries if r['candidate']=='working')
    primary=next(r for r in summaries if r['candidate']=='installed_primary')
    interpretation=(f"**Calculated direction of effects.** Primary lowers G1 assembly-bias RMS from {float(working['G1_16A_RMS_psi']):.2f} to {float(primary['G1_16A_RMS_psi']):.2f} psi on 16A and from {float(working['G1_16B_RMS_psi']):.2f} to {float(primary['G1_16B_RMS_psi']):.2f} psi on 16B. The G2 well biases move from {float(working['G2_16A_bias_kW']):.2f} to {float(primary['G2_16A_bias_kW']):.2f} kW and from {float(working['G2_16B_bias_kW']):.2f} to {float(primary['G2_16B_bias_kW']):.2f} kW, respectively. G6 regular-pipe bias increases from +{float(working['G6_regular_bias_C']):.2f} to +{float(primary['G6_regular_bias_C']):.2f} °C, and trial bias from +{float(working['G6_trial_bias_C']):.2f} to +{float(primary['G6_trial_bias_C']):.2f} °C. G4 run-in error RMS remains about {float(primary['G4_peak_error_RMS_C']):.1f} °C. These changes come from the summary columns above. **Inferred limit.** Improved aggregate pressure and power errors leave substantial temperature errors. The residual temperature errors and finished transition profile remain unresolved; the joint-loss contrast below addresses the additional warming.")
    recommendation=decision['recommendation'][0].upper()+decision['recommendation'][1:]
    text=f'''# Installed-pipe comparison results

**Calculated comparisons.** All variants use the declared frozen samples and settings. Bias is model minus observation. G1 on 16A compares standpipe pressure with measured standpipe minus raw motor differential; 16B G1 uses the four motorless assemblies. The two wells' G1 RMS values give equal weight to assembly biases. G2 uses the frozen in-hole hydraulic-power definition, including the retained raw motor face source, with surface power excluded. G3 is the 16A bit comparison. G4 retains the original run-in events and initial-state convention. G5 pools the 16A return observations. G6 separates regular and trial pipe on 16B.

## Six-gap results

**Calculated pressure and heat.** [summary.csv](summary.csv), columns `G1_16A_RMS_psi`, `G1_16B_RMS_psi`, `G2_16A_bias_kW`, `G2_16B_bias_kW`. The historical FH row comes unchanged from [entry 10 summary.csv](../../entry-10/results/summary.csv).

{pressure}

**Calculated temperatures.** The same file supplies `G3_16A_RMS_C`, `G4_peak_error_RMS_C`, `G5_16A_return_bias_C`, `G6_regular_bias_C` and `G6_trial_bias_C`.

{thermal}

{interpretation}

**Calculated assembly and event coverage.** [comparison.csv](comparison.csv) retains every gap, well and assembly/event group, its paired identifiers and before/after means, biases and errors. [comparison-with-entry10-fh.csv](comparison-with-entry10-fh.csv) adds the corresponding historical FH bias and model mean. [sample-changes.csv](sample-changes.csv) records each frozen sample's pressure, heat and temperature changes; [assembly-changes.csv](assembly-changes.csv) gives assembly means and ranges.

## G1 by assembly

**Calculated biases, psi.** Each value is `bias` in the relevant `results/<variant>/scoreboard.csv`, selected by `gap=G1`, `well` and `group`. The FH reference is `entry-10/results/fh/scoreboard.csv`. Primary and abrupt are identical by the declared source fallback, so they share a display column; both variants remain separate in the archive.

{chr(10).join(assembly_tables)}

## Secondary trip slopes

**Calculated measured/modelled ratios.** [secondary/slopes.csv](secondary/slopes.csv), columns `candidate`, `assembly`, `excursion`, `flow_centre_gpm`, `slope_ratio` and `added_pipe`. A ratio below one means the modelled pressure rise with added length is larger than measured. The FH reference comes from [entry 10 secondary/slopes.csv](../../entry-10/results/secondary/slopes.csv). EOW 19 adds insulated pipe and retains EIS connections in all installed variants; other groups add ordinary pipe. The no-local and global steel sensitivities have their separately declared scope.

{triptable}

{joint_loss_interpretation(out)}

**Calculated prediction reproduction.** {sum(r['passed']=='True' for r in checks)}/{len(checks)} representative circulation-field checks pass the declared 1-psi, 0.1-°C and 0.1%-power tolerances in [prediction-checks.csv](prediction-checks.csv). {sum(r['passed']=='True' for r in tripchecks)}/{len(tripchecks)} modelled trip-slope checks pass 1 psi/1000 ft in [secondary/prediction-checks.csv](secondary/prediction-checks.csv). The trip predictions were expressed before scoring as multipliers of the archived working ratio, with no new measured-pressure ratio computed. The scored values retain the original measured slopes and memberships. These are secondary diagnostics and do not select a transition or geometry.

## Coverage and limitations

**Calculated coverage.** Each variant retains all 467 circulation samples. Available and unavailable run-in identities are preserved. The child manifests identify every failed sample/event and every energy flag. Flags do not change solver success.

{failtable}

**Measured equipment record and inferred limits.** The ordinary-pipe dimensions are independently supplied by Kevin England, personal communication via John McLennan, November 2026, from the drill pipe data sheets. The declaration gives the complete source tables. The finished upset/weld/tool-joint profile remains unresolved. Restriction lengths are the recorded pin-plus-box tong approximations. The abrupt primary remains a source-gap fallback; score agreement does not establish a physical sharp transition. The zero-local-loss case is an idealised bound. The steel value is transferred from water pipe, with its global extension to insulated pipe explicitly qualified. No source supplies installed tool operating-loss curves.

**Calculated shallow diagnostic.** Entry 9 found 188–483 psi of modelled deficit in ten primary near-surface 16B windows. [shallow-diagnostic.csv](shallow-diagnostic.csv) replays all ten identities at their frozen mass rate and mean inlet/return temperature with working Colebrook and installed-primary geometry. Every partial-string geometry is identical and every installed pressure change is zero. The current remaining deficit is {shallow_min:.2f}–{shallow_max:.2f} psi; the small difference from the historical range is the retained Colebrook calculation. No circulation solve or coefficient fit is made. The source is [entry 9 near-surface.csv](../../entry-9/results/near-surface.csv); `shallow-manifest.json` records input and code hashes.

{shallow_table}

**Inferred remaining equipment gap.** The ordinary-pipe correction has no effect on these shallow partial strings. The 16B surface and BHA-tool losses remain unresolved at about 188–481 psi under this fixed-state diagnostic. No operating curve or extra surface allowance is obtained from that residual. The 16A shallow comparison remains unavailable because its recording periods have no shallow trip coverage; the tables above give its evaluated assembly changes.

**Inferred interpretation limit.** The G4 calculation retains the original approximate starting states, and changes can arise through conditioning circulation only. The historical trial-insulation fit remains present. FORGE 16A and 16B are development data. A new source correction or temperature improvement is not independent validation. No 58-32 data is used.

## Recommendation

**Calculated declared checks.** [decision.json](decision.json) records the paired-coverage and prediction checks without using score improvement as an adoption criterion.

**Inferred recommendation.** {recommendation}. The recommendation follows the independently sourced geometry and the declared reproduction rule, regardless of score direction. The abrupt treatment is the existing working treatment; the regular-pipe trip slopes show that it overstates per-length loss at the installed 3.0-in bore. It remains the declared unresolved-profile fallback. A later transition treatment requires an applicable sourced internal profile. No roughness or restriction length is fitted. Adoption of the sourced geometry, including whether to adopt before the transition treatment is sourced, remains Liam's decision as maintainer. Nothing is adopted in the package here.

## Reproduction and storage

**Calculated archive.** Complete per-sample score and rotary-application outputs are external. The entry-root [bulk-manifest.json](../bulk-manifest.json) records hashes, sizes and rebuild commands. Compact scoreboard, run-in and comparison results are committed. The child manifests distinguish their committed results from rebuildable bulk files. Rebuild the full scores in an external output directory using the declaration hash in the manifest, then run `compare.py` and the scoring mode of `trip_slopes.py`. `archive_results.py` rebuilds this compact archive. Input and code hashes are recorded in the final entry manifest. The declaration manifest describes the original declaration commit; later result documentation is identified separately. No package default or golden file changes.
'''
    (out/'README.md').write_bytes(text.encode('utf-8'))
    # Preserve the original reader-facing declaration, then append its result pointer.
    p=HERE/'README.md';s=p.read_text(encoding='utf-8')
    if '## Scored comparison' not in s:
        s+='\n## Scored comparison\n\n**Calculated.** The [results](results/README.md) report every gap and the secondary trip groups with paired coverage. The original source choices and model-only predictions above remain unchanged. Rebuildable bulk outputs are external and identified by hashes in [bulk-manifest.json](bulk-manifest.json).\n'
        p.write_bytes(s.encode('utf-8'))
    # Append results inside the existing chronological entry, without altering earlier entries.
    p=ROOT/'docs/science/model-development.md';s=p.read_text(encoding='utf-8')
    if '### Installed-pipe comparison results' in s:s=s.split('### Installed-pipe comparison results',1)[0].rstrip()+'\n'
    s=s.replace('Model-only predictions declared; frozen comparisons pending',
        'Frozen comparisons completed; see the six-gap and trip tables below')
    s=s.replace('No input adopted; abrupt fallback declared because finished taper geometry is unresolved',
        'Source-based recommendation recorded; adoption pending; finished taper geometry remains unresolved')
    s+='\n### Installed-pipe comparison results\n\n**Calculated.** [Entry 12 results](../../validation/model-development/entry-12/results/README.md) compare all six gaps on the unchanged frozen samples. Bias is model minus observation. G1 RMS gives equal weight to the assembly biases, with 16B restricted to its four motorless assemblies. The before result is entry 10 smooth; its historical FH result is a separate reference. Values below come from `summary.csv`; assembly and event detail is in `comparison.csv`.\n\n'+pressure+'\n\n'+thermal+'\n\n'+interpretation+'\n\n**Calculated assembly detail.** The [G1 tables](../../validation/model-development/entry-12/results/README.md#g1-by-assembly) give every 16A and motorless 16B assembly bias beside working and FH. The full comparison retains every G3 assembly and G4 event, with before/after coverage. Pressure and heat changes are in `sample-changes.csv` and `assembly-changes.csv`.\n\n**Calculated secondary slopes.** `secondary/slopes.csv`, column `slope_ratio`, retains all six original groups. Primary and abrupt are identical; EOW 19 adds insulated pipe with EIS dimensions.\n\n'+triptable+'\n\n'+joint_loss_interpretation(out,'../../validation/model-development/entry-12/results/',4)+'\n\n**Calculated reproduction.** '+str(sum(r['passed']=='True' for r in checks))+'/'+str(len(checks))+' representative field checks and '+str(sum(r['passed']=='True' for r in tripchecks))+'/'+str(len(tripchecks))+' modelled slope checks pass their declared tolerances. The child manifests retain failures and original unavailable run-in events. These checks do not use the direction of score changes.\n\n**Calculated shallow diagnostic and inferred equipment limit.** The ten original primary shallow 16B identities were replayed at their frozen mass rate and mean inlet/return temperature. Every working/installed-primary partial-string geometry is identical and every pressure change is zero. `shallow-diagnostic.csv` records the current Colebrook deficit of '+f'{shallow_min:.2f}–{shallow_max:.2f}'+' psi, about 188–481 psi, alongside the earlier entry 9 values. No circulation solve or coefficient fit is made. The ordinary-pipe correction therefore leaves the shallow surface/BHA-tool gap unresolved. A 16A shallow comparison remains unavailable; its G1 assembly changes are reported above.\n\n**Inferred recommendation.** '+recommendation+'. This follows the source correction and the predeclared prediction/coverage rule, regardless of score direction. The abrupt treatment is the existing working treatment. The regular-pipe trip slopes show that it overstates loss at the installed 3.0-in bore, so it remains a source-gap fallback pending the finished internal profile and an applicable gradual-loss treatment. The premium and transferred-steel cases remain sensitivities. No geometry, roughness or coefficient is selected by agreement. The historical trial-insulation fit remains disclosed. Adoption, including whether to adopt before the transition treatment is sourced, remains Liam\'s decision as maintainer. Package defaults and goldens remain unchanged.\n'
    p.write_bytes(s.encode('utf-8'))
    files=[p for p in HERE.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.name!='manifest.json']
    # Include nested manifests explicitly while excluding only the root manifest itself.
    files=[p for p in HERE.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p!=HERE/'manifest.json']
    (HERE/'manifest.json').write_bytes((json.dumps(dict(declaration_commit=decision['declaration_commit'],
        package_defaults_changed=False,adopted=False,
        files_sha256={p.relative_to(HERE).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(files)}),indent=2)+'\n').encode('utf-8'))
    print('Reader-facing six-gap results, source-based recommendation and final manifest written.')


if __name__=='__main__':main()
