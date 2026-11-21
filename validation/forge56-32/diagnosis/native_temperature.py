"""Read the native 56-32 temperature logs and compare them with the 16A transfer.

usage: native_temperature.py ARCHIVE OUTPUT

ARCHIVE is GDR 1295 (`1295.zip`), read in place. Two LAS files in it carry
a temperature curve:

  56-32 Cement Bond.zip!...CBL_Main_17Aug21_LAS.las   MTEM, mud temperature,
      60 to 9,111 ft MD, logged on 17 August 2021 in the cased well
  Schlumberger_56-32.zip!Wireline Field Data/...ThruBit_Main.las   WTEP_TMG,
      3,450 to 9,127 ft MD, logged on 27 February 2021 after circulation

OUTPUT receives:

  native_temperature_logs.csv  every finite sample, with TVD from the
                               56-32 survey and the 16A-transferred
                               formation temperature at that TVD
  formation_comparison.csv     100 ft TVD bins from 0 to 5,500 ft
  native_temperature-source.json  members, headers and hashes

Log depths are taken as measured depth on the survey's reference. The
nested archives are stored without compression, so each LAS member is
read from its byte range in ARCHIVE.
"""
import argparse
import csv
import hashlib
import io
import json
import struct
from pathlib import Path
import re
import zipfile

import numpy as np

from borethm.studies import validate_forge16a as a
from importlib import import_module

pressure = import_module("validation.forge56-32.compare_pressure")
LOGS = {
    "cbl_mtem": ("56-32 Cement Bond.zip", "UniversityofUtah_Forge56-32_MonitorWell_CBL_Main_17Aug21_LAS.las", "MTEM"),
    "thrubit_wtep": ("Schlumberger_56-32.zip",
                     "Wireline Field Data/A.1008700.02.01_UniversityUtah_Forge-56-32_ThruBit_Main.las", "WTEP_TMG"),
}
FT = 0.3048
BIN_FT = 100.
MAX_TVD_FT = 5500.


class Slice(io.RawIOBase):
    """A read-only window onto a byte range of an open file."""

    def __init__(self, stream, start, length):
        self.stream, self.start, self.length, self.pos = stream, start, length, 0

    def readable(self):
        return True

    def seekable(self):
        return True

    def tell(self):
        return self.pos

    def seek(self, offset, whence=0):
        self.pos = {0: offset, 1: self.pos+offset, 2: self.length+offset}[whence]
        return self.pos

    def readinto(self, buffer):
        n = max(0, min(len(buffer), self.length-self.pos))
        self.stream.seek(self.start+self.pos)
        data = self.stream.read(n)
        buffer[:len(data)] = data
        self.pos += len(data)
        return len(data)


def stored(stream, top, name):
    info = top.getinfo(name)
    if info.compress_type != zipfile.ZIP_STORED:
        raise ValueError(f"{name} is compressed; this reader needs a stored member")
    stream.seek(info.header_offset)
    n, m = struct.unpack("<HH", stream.read(30)[26:30])
    return Slice(stream, info.header_offset+30+n+m, info.compress_size)


def parse_las(text, curve):
    """Depth and one curve from a LAS 2.0 file without wrapped lines."""
    sections = re.split(r"^~", text, flags=re.M)
    version = next(s for s in sections if s[:1].upper() == "V")
    if re.search(r"^\s*WRAP\s*\.\s*YES", version, re.M | re.I):
        raise ValueError("wrapped LAS is not supported")
    curves = next(s for s in sections if s[:1].upper() == "C")
    names = [line.split(".")[0].strip() for line in curves.splitlines()[1:]
             if line.strip() and not line.lstrip().startswith("#")]
    well = next(s for s in sections if s[:1].upper() == "W")
    null = float(re.search(r"^\s*NULL\s*\.\s*(\S+)", well, re.M)[1])
    data = next(s for s in sections if s[:1].upper() == "A")
    values = np.array([[float(x) for x in line.split()] for line in data.splitlines()[1:] if line.strip()])
    if values.shape[1] != len(names):
        raise ValueError(f"{len(names)} curves against {values.shape[1]} columns")
    depth, temp = values[:, 0], values[:, names.index(curve)]
    keep = np.isfinite(temp) & (temp != null) & (depth != null)
    unit = re.search(rf"^\s*{curve}\s*\.(\S*)", curves, re.M)[1]
    header = {k: re.search(rf"^\s*{k}\s*\.[^\n]*", well, re.M)[0].strip()
              for k in ("STRT", "STOP", "DATE") if re.search(rf"^\s*{k}\s*\.", well, re.M)}
    return depth[keep], temp[keep], unit, header


def read_logs(archive):
    out, source = {}, {}
    with open(archive, "rb") as stream:
        top = zipfile.ZipFile(stream)
        for key, (outer, member, curve) in LOGS.items():
            inner = zipfile.ZipFile(stored(stream, top, outer))
            raw = inner.read(member)
            md, temp, unit, header = parse_las(raw.decode("latin-1"), curve)
            if unit.upper() != "DEGF":
                raise ValueError(f"{key}: unexpected unit {unit}")
            out[key] = (md, (temp-32)/1.8)
            source[key] = dict(member=f"{outer}!{member}", sha256=hashlib.sha256(raw).hexdigest(),
                               curve=curve, unit=unit, header=header, samples=int(len(md)))
    return out, source


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("archive", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    logs, source = read_logs(args.archive)
    survey = pressure.survey()
    transfer = a.formation("216", a.survey())[0]
    rows = []
    for key, (md, temp) in logs.items():
        tvd = survey.tvd(md*FT)/FT
        for d, z, t in zip(md, tvd, temp):
            rows.append(dict(log=key, md_ft=float(d), tvd_ft=float(z), temperature_C=float(t),
                             transfer_16a_C=float(transfer(z*FT))))
    args.output.mkdir(parents=True, exist_ok=True)
    with open(args.output/"native_temperature_logs.csv", "w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    bins = []
    for top in np.arange(0., MAX_TVD_FT, BIN_FT):
        row = dict(tvd_top_ft=top, tvd_bottom_ft=top+BIN_FT,
                   transfer_16a_C=float(transfer((top+BIN_FT/2)*FT)))
        for key in logs:
            sel = [r["temperature_C"] for r in rows if r["log"] == key and top <= r["tvd_ft"] < top+BIN_FT]
            row[f"{key}_C"] = float(np.mean(sel)) if sel else ""
            row[f"{key}_samples"] = len(sel)
            row[f"{key}_minus_transfer_C"] = row[f"{key}_C"]-row["transfer_16a_C"] if sel else ""
        bins.append(row)
    with open(args.output/"formation_comparison.csv", "w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, list(bins[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(bins)
    source["transfer"] = "validation/forge16a/formation_temperature_216day.csv by TVD (validate_forge16a.formation)"
    source["tvd"] = "validation/forge56-32/survey.csv (compare_pressure.survey)"
    (args.output/"native_temperature-source.json").write_text(json.dumps(source, indent=2)+"\n",
                                                               encoding="utf-8", newline="\n")
    print(json.dumps({k: v["samples"] for k, v in source.items() if isinstance(v, dict)}))


if __name__ == "__main__":
    main()
