"""Assembly sheets and components of 78B-32 from the end-of-well report.

The BHA tables of `78B-32 EOWR Final.pdf` are images. `--ocr` recognises
the listed pages with RapidOCR (rapidocr-onnxruntime 1.4.4, pdfplumber
0.11.10, 200 dpi) and writes the text to `inputs/bha-sheets-ocr.txt`. A first
pass printed every page with its digits masked and listed any word that
suggests a temperature or a pressure; the only such words were motor bend
angles ("1.5 DEG"), so the pages hold no sealed value.

Without `--ocr` the script parses the committed text. Each sheet's component
lengths are summed and compared with its printed BHA length. Rows that OCR
misread were checked against the page images and are corrected below, each
with its reason. A sheet whose sum still differs is flagged.

Usage: python build_bha_sheets.py [--ocr ARCHIVE]
"""
import argparse
import csv
import io
from pathlib import Path
import re
import zipfile

HERE = Path(__file__).resolve().parent
OCR_TEXT = HERE/"inputs"/"bha-sheets-ocr.txt"
EOWR = "78B-32 EOWR Final.pdf"
PAGES = [29, 35, 36, 37, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 64, 65]

ITEMS = r"CORBIT|CORBT|BIT|Coring Bit|BS|XO|MWD|MONEL|FLOAT|OTHER|HWDP|DC|MMTR|STAB|RR|CORE|NMDC|JAR|JARS"
ROW = re.compile(rf"^\s*({ITEMS})\.?\s*\|\s*(.*)$")
NUM = re.compile(r"^\d[\d,]*(\.\d+)?$|^\.\d+$")
# A number fused to a grade, such as "77.4S-135", is a weight.
LEAD = re.compile(r"^(\d[\d,]*\.\d+|\d+)(?=[S5][-.]?\d)")
BITS = ("BIT", "Coring Bit", "CORBT", "CORBIT")

# (BHA, row): corrected (jnts, length ft, OD in, ID in), checked against the page image.
CORRECT = {
    ("17", 7): ("1", 3.12, 6.75, 3.0),     # p56: OCR dropped the joint count and shifted the row
    ("18", 2): ("1", 3.20, 8.0, ""),       # p56: bit sub, no ID printed
    ("22", 3): ("1", 9.99, 4.75, 2.36),    # p65: pony collar, OCR read 9.99 as 666
}
# (BHA, insert before row): missing rows, read from the page image.
INSERT = {
    ("14", 1): ("BIT", "1", 0.92, 10.625, "", "S/No: A279636"),   # p53
    ("20", 2): ("BS", "1", 3.20, 8.0, "", "Dressed with float"),  # p57
}
# Printed fields OCR missed, read from the page image.
SHEET_FIELDS = {
    "16": dict(bha_length_ft=509.79),          # p55
    "20": dict(bha_length_ft=469.42),          # p57
    "22": dict(depth_in_source="8,555"),       # p65: OCR read 8,665; the sheet prints its depth out as "10"
}


def num(s):
    return float(s.replace(",", ""))


def numbers(rest):
    out = []
    for part in re.split(r"\s*\|\s*|\s+", rest):
        if not part:
            continue
        if NUM.match(part):
            out.append(num(part))
            continue
        m = LEAD.match(part)
        if m:
            out.append(num(m[1]))
        break
    return out


def ocr(archive):
    import numpy as np
    import pdfplumber
    from rapidocr_onnxruntime import RapidOCR
    engine = RapidOCR()
    out = []
    with zipfile.ZipFile(archive) as zf, pdfplumber.open(io.BytesIO(zf.read(EOWR))) as pdf:
        for n in PAGES:
            img = np.array(pdf.pages[n-1].to_image(resolution=200).original.convert("RGB"))
            result, _ = engine(img)
            boxes = sorted((np.mean([p[1] for p in b]), min(p[0] for p in b), t) for b, t, _ in result or [])
            rows, cur, y0 = [], [], None
            for y, x, t in boxes:
                if y0 is not None and y - y0 > 12:
                    rows.append(cur); cur = []
                    y0 = y
                if y0 is None:
                    y0 = y
                cur.append((x, t))
            if cur:
                rows.append(cur)
            out.append(f"==== page {n}")
            out += ["   " + " | ".join(t for _, t in sorted(r)) for r in rows]
    OCR_TEXT.write_text("\n".join(out) + "\n", encoding="utf-8")


def parse(text):
    sheets, comps, page, sheet = [], [], None, None
    for line in text.splitlines():
        m = re.match(r"^==== page (\d+)", line)
        if m:
            page = int(m[1]); continue
        s = line.strip()
        cap = re.search(r"Table (\d+):.*?BHA\s*#\s*(\d+)", s)
        if cap:
            sheet = dict(page=page, table=cap[1], caption_bha=cap[2]); sheets.append(sheet); continue
        if sheet is None:
            continue
        if re.match(r"BHA ?No", s):
            m = re.search(r"No[:.]?\s*(\d+)", s)
            if sheet.get("bha") or sheet.get("depth_in_source"):
                sheet = dict(page=page, table="", caption_bha=""); sheets.append(sheet)
            if m:
                sheet["bha"] = m[1]
        elif s.startswith("BHA Length"):
            v = s.split("|")[-1].strip()
            sheet["bha_length_ft"] = num(v.replace(".", ",", v.count(".") - 1))
        elif re.match(r"Depth ?\(ft\)", s):
            c = [x.strip() for x in s.split("|")[1:]] + ["", ""]
            sheet["depth_in_source"], sheet["depth_out_source"] = c[:2]
        elif s.startswith("Date/Time"):
            c = [x.strip() for x in s.split("|")[1:]] + ["", ""]
            sheet["date_in_source"], sheet["date_out_source"] = c[:2]
        elif s.startswith("Comments") and "comments" not in sheet:
            sheet["comments"] = s.split(":", 1)[-1].strip(" |")
        else:
            r = ROW.match(line)
            if not r:
                continue
            item, rest = r[1], r[2]
            n = numbers(rest)
            want = 2 if item in BITS else 4
            jnts, vals = (str(int(n[0])), n[1:]) if len(n) == want + 1 else ("", n)
            comps.append(dict(sheet=sheet, item=item, jnts=jnts,
                              length_ft=vals[0] if vals else "", od_in=vals[1] if len(vals) > 1 else "",
                              id_in="" if item in BITS else (vals[2] if len(vals) > 2 else ""),
                              comment=[c.strip() for c in rest.split("|")][-1], source="ocr"))
    return sheets, comps


def depth(text):
    t = text.strip()
    if re.fullmatch(r"\d{1,2}[.,]\d{3}", t):      # OCR reads the thousands comma as a point
        t = t.replace(".", ",")
    try:
        return float(t.replace(",", ""))
    except ValueError:
        return ""


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--ocr", type=Path, help="archive to run OCR on before parsing")
    args = ap.parse_args()
    if args.ocr:
        ocr(args.ocr)
    sheets, comps = parse(OCR_TEXT.read_text(encoding="utf-8"))
    rows_out = []
    for sh in sheets:
        bha = sh.get("bha") or sh["caption_bha"]
        sh.update(SHEET_FIELDS.get(bha, {}))
        rows = [c for c in comps if c["sheet"] is sh]
        fixed = []
        for i, c in enumerate(rows, 1):
            if (bha, i) in INSERT:
                item, j, ln, od, idn, com = INSERT[(bha, i)]
                fixed.append(dict(item=item, jnts=j, length_ft=ln, od_in=od, id_in=idn, comment=com, source="page image"))
            if (bha, i) in CORRECT:
                j, ln, od, idn = CORRECT[(bha, i)]
                c = dict(c, jnts=j, length_ft=ln, od_in=od, id_in=idn, source="page image")
            fixed.append(c)
        total = 0.0
        for k, c in enumerate(fixed, 1):
            total += c["length_ft"] if c["length_ft"] != "" else 0.0
            rows_out.append(dict(bha=bha, row=k, item=c["item"], jnts=c["jnts"], length_ft=c["length_ft"],
                                 od_in=c["od_in"], id_in=c["id_in"], comment=c["comment"], source=c["source"],
                                 page=sh["page"]))
        sh.update(bha=bha, depth_in_ft=depth(sh.get("depth_in_source", "")),
                  depth_out_ft=depth(sh.get("depth_out_source", "")), components=len(fixed),
                  component_sum_ft=round(total, 2),
                  length_check="matches" if abs(total - sh.get("bha_length_ft", -1)) < 0.02 else "differs")
    fields = ["bha", "page", "table", "caption_bha", "depth_in_source", "depth_out_source", "depth_in_ft",
              "depth_out_ft", "date_in_source", "date_out_source", "bha_length_ft", "component_sum_ft",
              "length_check", "components", "comments"]
    for name, rows, f in (("bha_sheets.csv", sheets, fields), ("bha_components.csv", rows_out, None)):
        f = f or list(rows[0])
        with open(HERE/"inputs"/name, "w", encoding="utf-8", newline="") as fh:
            w = csv.DictWriter(fh, f, extrasaction="ignore", lineterminator="\n")
            w.writeheader(); w.writerows(rows)
    for sh in sheets:
        print(f"BHA {sh['bha']:>3} p{sh['page']:<3} {sh['depth_in_ft']!s:>7}-{sh['depth_out_ft']!s:<7} "
              f"{sh.get('date_in_source', '')} -> {sh.get('date_out_source', '')}  "
              f"length {sh.get('bha_length_ft', '?')} sum {sh['component_sum_ft']} {sh['length_check']}")


if __name__ == "__main__":
    main()
