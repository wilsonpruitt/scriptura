# Scriptura — preliminary findings (2026-11-10)

Proof-of-concept material. Every number is from spine v0 and the sensus ledgers, computed with no
model tokens. Everything here is **provisional**: the exclusion list is unruled, the PG is not yet
read, and Migne's own citations follow each volume's editor (see `studies/canon/STUDY.md`).
Publishable as aggregate findings. The de Lubac ledger itself (in-copyright citation strings) stays
local.

## 1. What each age quoted most (the working canon)

Migne's own in-text verse citations, counted as **distinct works citing the verse**
(`spine-inline.tsv`, verse level, verse exists in the Clementine). These are his editors'
identifications, so the matchers' noise does not enter:

| to 600 (558 works) | 601–1000 (406) | 1001–1216 (583) |
|---|---|---|
| John 1:1 (119) | John 14:6 (46) | John 14:6 (56) |
| John 1:14 (102) | Matt 25:34 (45) | Matt 11:29 (53) |
| John 10:30 (92) | Matt 11:29 (39) | John 1:1 (49) |
| John 1:3 (89) | Matt 28:20 (34) | Phil 3:20 (49) |
| John 14:6 (84) | John 1:1 (34) | Jas 1:17 (47) |
| Phil 2:6 (83) | Jas 1:17 (34) | John 1:14 (47) |
| Rom 5:5 (74) | John 1:14 (33) | Acts 4:32 (42) |
| Matt 28:19 (73) | Matt 5:44 (31) | Gal 6:14 (41) |
| Gen 1:26 (70) | Matt 28:19 (31) | Phil 1:23 (41) |
| 1 Tim 2:5 (66) | Matt 25:41 (30) | Matt 5:3 (40) |

- **To 600:** Christology and the Trinity. John 1, "ego et pater unum sumus", the kenosis of
  Philippians 2, "unus mediator". The controversies show in the counts.
- **601–1000:** judgment and the Christian life. The Last Judgment (Matt 25:34, 41), "discite a me
  quia mitis sum", love of enemies.
- **1001–1216:** the religious life. "Cor unum et anima una" (Acts 4:32, the text of the Rule of
  Augustine and the canons regular), "nostra conversatio in caelis", "cupio dissolvi", "mihi absit
  gloriari nisi in cruce", "beati pauperes spiritu".

With the n-gram and fuzzy streams added (`studies/canon/scripts/headline.py`), 34,455 of the
35,811 Vulgate verses are cited at least once in the PL. **1,356 (3.8%) never are.** They cluster
in Baruch (55%, mostly the Letter of Jeremiah), 1–2 Maccabees (41–42%), Ezra–Nehemiah (14%),
Joshua and Numbers. Every verse of 1 John, 1 Peter, 1 Timothy, 2 Corinthians, Colossians, Amos and
the Song of Songs is cited somewhere. Caveat: the merged count still holds formulas. Matt 28:19
leads every age in it because of "in nomine patris et filii et spiritus sancti".

## 2. The four senses, stated (sensus stage D)

- 269 passages in the PL name three or more senses within 60 words. Two blind codings agree on
  kind (kappa 0.93). 132 are statements of theory.
- The earliest four-fold statements: Cassian (*Conl.* XIV.8, PL 49, 962 C), then Eucherius (PL
  50, 728 B), then Bede. The canonical order history, allegory, tropology, anagogy is first stated
  by **Bede, *De tabernaculo*** (PL 91, 410 B), then Amalarius and Rabanus.
- The figure most used to teach the senses is **Jerusalem** (28 passages); next is the four feet
  of the tabernacle table (5).

## 3. What a machine finds, and what only a reader finds

- De Lubac cites 96 of the 132 theory statements for theory. 11 he does not cite at all; these are
  candidates for a reader to confirm, not yet claims.
- Of his PL theory citations naming three or more senses, the census lands on half (222 of 440).
  Of the misses, 98 places are rules the census could relax (window, broad terms). **64 are
  schemes carried by figures**: the three ways of cooking a sacrifice, four casks in a cellar,
  shadow / image / truth. No vocabulary finds these. That is de Lubac's own contribution, and the
  reason the reading layer exists.

## 4. Which Bible were they quoting?

Matched against the Clementine Vulgate, the spine finds 29% of Migne's verse citations for
Fathers who died by 400, and about 50% after 600. With an Old Latin index (Sabatier 1743; the
IGNTP's 37 Old Latin manuscripts of John, CC BY 4.0), recall on the early Fathers' NT citations
rises by about 4 points overall and 7 on John. Much of what remains is allusion, not quotation: the
early Fathers cite differently, not only from a different text.
