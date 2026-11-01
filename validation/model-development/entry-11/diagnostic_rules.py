"""Source-time period selection, independent of pressure values."""
from datetime import datetime


def epoch_seconds(times):
    """Use explicit elapsed seconds, independent of a reader's time unit."""
    origin = datetime(1970, 1, 1)
    return [(value-origin).total_seconds() for value in times]


def spells(seconds, selected, maximum_gap=2):
    """Return half-open index ranges of selected, source-contiguous rows."""
    start = None
    for i, chosen in enumerate(selected):
        gap = i > 0 and (seconds[i]-seconds[i-1] > maximum_gap or seconds[i] < seconds[i-1])
        if start is not None and (not chosen or gap):
            yield start, i
            start = None
        if chosen and start is None:
            start = i
    if start is not None:
        yield start, len(seconds)


def retained_off_indices(seconds, p1, p2, settle=60, minimum=60):
    """Discard pumps-off settling; retain at least 60 observed seconds."""
    selected = [a == 0 and b == 0 for a,b in zip(p1,p2)]
    for start,end in spells(seconds,selected):
        keep = [i for i in range(start,end) if seconds[i] >= seconds[start]+settle]
        if keep and seconds[keep[-1]]-seconds[keep[0]]+1 >= minimum:
            yield keep
