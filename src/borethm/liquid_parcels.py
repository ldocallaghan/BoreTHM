"""Piecewise constant liquid parcels in the volume coordinate."""
from dataclasses import dataclass

import numpy as np

from .run_in_column import volume_remap


@dataclass
class Parcels:
    volume: np.ndarray
    temperature: np.ndarray

    @property
    def size(self):
        return float(np.sum(self.volume))

    @property
    def inventory(self):
        return float(np.dot(self.volume, self.temperature))

    def slice(self, first, last):
        """Clip parcels to a volume interval while preserving each temperature."""
        faces = np.r_[0., np.cumsum(self.volume)]
        sizes = np.maximum(0., np.minimum(faces[1:], last)-np.maximum(faces[:-1], first))
        keep = sizes > 0.
        return Parcels(sizes[keep], self.temperature[keep])

    def fitted(self, total, tolerance=1e-9):
        """Give a rounding gap in the total volume to the largest parcel.

        Repeated slicing loses or gains volume at the rounding level. A gap
        larger than the relative tolerance is an error, not rounding.
        """
        gap = total-self.size
        if not gap:
            return self
        largest = int(np.argmax(self.volume))
        if abs(gap) > tolerance*max(total, 1e-300) or self.volume[largest]+gap <= 0.:
            raise ValueError(f"parcel volume {self.size!r} differs from the conduit volume {total!r}")
        volume = self.volume.copy()
        volume[largest] += gap
        return Parcels(volume, self.temperature)

    def reversed(self):
        return Parcels(self.volume[::-1], self.temperature[::-1])

    def join(self, other):
        return Parcels(np.r_[self.volume, other.volume],
                       np.r_[self.temperature, other.temperature])

    def averages(self, cells):
        if not len(cells):
            return np.empty(0)
        return volume_remap(self.volume, self.temperature, cells)

    def with_cell_heat(self, cells, temperatures):
        """Apply each cell's uniform temperature increment to its parcels."""
        if not len(cells):
            return self
        increment = temperatures-self.averages(cells)
        if np.max(np.abs(increment)) < 1e-11:
            return self
        parcel_faces = np.r_[0., np.cumsum(self.volume)]
        cell_faces = np.r_[0., np.cumsum(cells)]
        faces = np.unique(np.r_[parcel_faces, cell_faces[1:-1]])
        mid = faces[:-1] + np.diff(faces)/2
        parcel_index = np.minimum(np.searchsorted(parcel_faces, mid, side="right")-1,
                                  len(self.volume)-1)
        cell_index = np.minimum(np.searchsorted(cell_faces, mid, side="right")-1,
                                len(cells)-1)
        return Parcels(np.diff(faces), self.temperature[parcel_index]+increment[cell_index])

    def heat_interval(self, first, last, change):
        """Add a temperature increment over a parcel interval."""
        portion = self.slice(first, last)
        heated = Parcels(portion.volume, portion.temperature+change)
        return self.slice(0., first).join(heated).join(self.slice(last, self.size))
