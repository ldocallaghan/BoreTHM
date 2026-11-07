"""Time and flow rules for staged trips and drilling pauses."""
from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class History:
    """Aligned regular or gappy records, time in integer seconds."""
    time: np.ndarray
    bit: np.ndarray
    hole: np.ndarray
    flow: np.ndarray
    rpm: np.ndarray
    step: int

    def spells(self, mask, first=0, end=None):
        indices = np.flatnonzero(mask[first:end]) + first
        if not len(indices):
            return
        split = np.flatnonzero((np.diff(indices) != 1) |
                               (np.diff(self.time[indices]) != self.step)) + 1
        for group in np.split(indices, split):
            yield int(group[0]), int(group[-1]) + 1

    def duration(self, first, end):
        return int(self.time[end - 1] - self.time[first] + self.step)

    def bounds(self, first, end):
        return int(self.time[first]), int(self.time[end - 1] + self.step)

    def _bottom_rows(self):
        return np.flatnonzero((self.hole > 0) & (self.bit > 0) &
                              (np.abs(self.hole - self.bit) <= 5.))

    def trip_stages(self, first=0, bottom=None):
        if bottom is None:
            reached = self._bottom_rows()
            if not len(reached):
                return
            bottom = int(reached[0])
        start = first
        for left, right in self.spells(self.flow > 100, first):
            if left > bottom:
                break
            if self.duration(left, right) <= 60:
                continue
            if start < left:
                yield start, left, left, right
            start = right
        if start < bottom:
            yield start, bottom, None, None

    def drilling_pauses(self, first=None, end=None):
        reached = self._bottom_rows()
        if not len(reached):
            return
        first = int(reached[0] + 1) if first is None else first
        end = int(reached[-1] + 1) if end is None else end
        lead = {b: a for a, b in self.spells(self.flow > 100) if self.duration(a, b) >= 600}
        for left, right in self.spells((self.flow >= 0) & (self.flow < 50), first, end):
            if left in lead and self.duration(left, right) >= 60:
                if self.time[left] - self.time[left - 1] == self.step:
                    yield left, right, lead[left]


def pause_class(seconds):
    if seconds <= 600:
        return "connection"
    return "stop" if seconds <= 7200 else "long_stop"


def availability(history, mask, start, end):
    """Report observed fraction and longest missing span, including edge gaps."""
    good = history.time[mask & (history.time >= start) & (history.time < end)]
    if end <= start:
        return 0., 0
    covered = len(good) * history.step
    gaps = np.diff(np.r_[start - history.step, good, end]) - history.step
    return min(1., covered / (end - start)), int(max(0, gaps.max()))
