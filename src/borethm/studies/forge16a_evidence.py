"""Recompute summaries of frozen FORGE 16A predictions without model solves.

These archival checks verify the published comparison arithmetic. They do not
test a later numerical model against the original experiment by rerunning it.
"""
import csv
import math
import statistics
from collections import defaultdict
from borethm._paths import repository_path, require_path

DATA=repository_path('validation/forge16a')
BRANCHES=('bore_bit_C','bore_40ft_C','annulus_bit_C','annulus_40ft_C')


def primary_records(data=None):
    """Saved primary circulation predictions and matched observations."""
    archive=require_path(data if data is not None else DATA, 'FORGE 16A evidence archive')
    with (archive/'circulation-primary.csv').open(newline='') as f:
        return list(csv.DictReader(f))


def _metrics(pairs):
    model,observed=zip(*pairs)
    delta=[m-o for m,o in pairs]
    return dict(n=len(pairs),measured_mean_C=statistics.mean(observed),model_mean_C=statistics.mean(model),
                ME_C=statistics.mean(delta),MAE_C=statistics.mean(map(abs,delta)),
                RMSE_C=math.sqrt(statistics.mean(d*d for d in delta)),max_abs_C=max(map(abs,delta)),
                MAPE_K_percent=100*statistics.mean(abs(m-o)/(o+273.15) for m,o in pairs))


def primary_summary(data=None):
    """Per-run and pooled statistics, retaining each fixed sensor comparison."""
    q1,q2=defaultdict(list),defaultdict(list)
    for row in primary_records(data):
        if row['success']!='True':
            raise ValueError('The frozen primary archive contains an unsuccessful case')
        groups=[row['run'],'ALL']
        if row['washout']!='True':groups.append('ALL excluding washout')
        for run in groups:
            q2['|'.join((row['source'],run))].append((float(row['return_C']),float(row['measured_return_C'])))
            for ch in ('bit_box_C','top_sub_C'):
                if row.get('measured_'+ch):
                    for branch in BRANCHES:
                        q1['|'.join((run,ch,branch))].append((float(row[branch]),float(row['measured_'+ch])))
    return dict(q1={key:_metrics(pairs) for key,pairs in q1.items()},
                q2={key:_metrics(pairs) for key,pairs in q2.items()})
