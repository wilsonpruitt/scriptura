#!/usr/bin/env python3
"""Build a PL locator: (volume, column) -> work, from the Corpus Corporum TEI on disk.

Reads  ~/patrologia/sources/pl/tei/*.xml  and  ~/patrologia/data/cc-pl-index.json
Writes data/pl-locator.tsv  (one row per work per volume: column span + author + year)
       data/pl-columns.json (volume -> {column -> [idno,...]}), used by resolve step.
No model tokens. Re-run whenever the TEI set changes.
"""
import json, re, sys, collections
from pathlib import Path

PAT = Path.home() / "patrologia"
OUT = Path(__file__).resolve().parent.parent / "data"
idx = json.load(open(PAT / "data/cc-pl-index.json"))["works"]
meta = {}
for w in idx:
    for t in w["texts"]:
        meta[t["idno"]] = (w["author"], w.get("authorYear") or "", re.sub(r",? J\. ?P\. Migne$", "", t["name"]))

vol_re = re.compile(r"Patrologia Latina,?\s*vol\.?\s*(\d+)", re.I)
pb_re = re.compile(r'<pb\b[^>]*\bn="(\d{1,4})([A-D]?)[^"]*"')
cols = collections.defaultdict(lambda: collections.defaultdict(set))  # vol -> col -> {idno}
rows, novol, nopb = [], [], []
for f in sorted((PAT / "sources/pl/tei").glob("*.xml"), key=lambda p: int(p.stem) if p.stem.isdigit() else 0):
    s = f.read_text(encoding="utf-8", errors="replace")
    m = vol_re.search(s[:6000])
    if not m:
        novol.append(f.stem); continue
    vol = int(m.group(1))
    cs = sorted({int(c) for c, _ in pb_re.findall(s)})
    if not cs:
        nopb.append(f.stem); continue
    for c in cs:
        cols[vol][c].add(f.stem)
    a, y, t = meta.get(f.stem, ("", "", ""))
    rows.append((vol, cs[0], cs[-1], len(cs), f.stem, a, y, t))

rows.sort()
OUT.mkdir(exist_ok=True)
with open(OUT / "pl-locator.tsv", "w", encoding="utf-8") as o:
    o.write("volume\tcol_first\tcol_last\tn_cols\tidno\tauthor\tauthor_year\ttitle\n")
    for r in rows:
        o.write("\t".join(str(x) for x in r) + "\n")
json.dump({str(v): {str(c): sorted(i) for c, i in sorted(d.items())} for v, d in sorted(cols.items())},
          open(OUT / "pl-columns.json", "w"))
print(f"works located: {len(rows)}; volumes: {len(cols)}; files without volume: {len(novol)}; without <pb>: {len(nopb)}")
print("missing volumes 1-217:", [v for v in range(1, 218) if v not in cols])
print("no-volume sample:", novol[:10], "no-pb sample:", nopb[:10])
