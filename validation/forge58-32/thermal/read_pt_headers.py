"""Read whitelisted header keys from the reserved 58-32 PT logs.

The PT logs in 1006.zip are reserved thermal targets. This reader keeps only
the ~Well keys listed in KEEP and the sheet names of the November workbook.
Every other key, every other LAS section and every data row is dropped
before anything is printed or saved. Parsing stops at the first section
after ~Well, so curve, parameter, other and data sections are never read.
"""
import argparse
import csv
import io
from pathlib import Path
import zipfile

KEEP = ("DATE", "STRT", "STOP", "STEP", "TDL1", "TLOB1", "TCS1")
WORKBOOK = "PT/Nov 2 PT survey.xlsx"


def well_keys(stream):
    """Yield (key, unit, value) for whitelisted ~Well lines only."""
    section = ""
    for raw in stream:
        line = raw.strip()
        if line.startswith("~"):
            if section == "W":
                return  # ~Well has ended: stop before any later section is read
            section = line[1:2].upper()
            continue
        if section != "W" or not line or line.startswith("#") or "." not in line:
            continue
        key, rest = line.split(".", 1)
        key = key.strip()
        if key not in KEEP:
            continue
        # LAS 2.0: MNEM.UNIT  VALUE : DESCRIPTION. The description follows the
        # last colon and is dropped; a time value can contain colons itself.
        unit, _, value = rest.partition(" ")
        value = value.rsplit(":", 1)[0].strip()
        yield key, unit.strip(), value


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("archive", type=Path, help="1006.zip")
    parser.add_argument("output", type=Path, help="CSV to write")
    args = parser.parse_args()
    rows = []
    with zipfile.ZipFile(args.archive) as top:
        with zipfile.ZipFile(io.BytesIO(top.read("58-32_PT_logs.zip"))) as archive:
            for name in sorted(archive.namelist()):
                if name.lower().endswith(".las"):
                    with io.TextIOWrapper(archive.open(name), encoding="latin1") as stream:
                        for key, unit, value in well_keys(stream):
                            rows.append(dict(source=name, key=key, unit=unit, value=value))
            from openpyxl import load_workbook
            book = load_workbook(io.BytesIO(archive.read(WORKBOOK)), read_only=True)
            for sheet in book.sheetnames:
                rows.append(dict(source=WORKBOOK, key="sheet_name", unit="", value=sheet))
            book.close()
    assert all(r["key"] in KEEP + ("sheet_name",) for r in rows)
    with args.output.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, ("source", "key", "unit", "value"), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    print(f"{len(rows)} whitelisted header fields written")


if __name__ == "__main__":
    main()
