# LAYERS.md: the layer registry

PLAN section 2. One row per existing layer, **read from the repos, not from memory**: surveyed
read-only on 2026-11-10 by three agents. Counts are measured, not taken from READMEs, unless
marked "stated". ⚠ The survey read the local clones: pull before trusting a 'none stated' (four licences on GitHub were missed). Spot-checked by hand: reception-corpus at 115,810 rows (its README says 101,353),
the KJV at 31,100 verses (31,102 is correct; see flags), and migne.app's Ps.118 at 85 records
(Vulgate numbering).

**The join standard this registry measures against:** OSIS `refKey` (`Gen.1.1`, ranges
`Matt.1.1-Matt.1.17`) on KJV/WEB versification. That is what reception-corpus, catena and fons
already use, and what PLAN section 2 names. "Adapter" below means what a layer needs before it
can join on that key.

## 1. Text: what it says

| layer | repo | holds | key as stored | coverage | versification | licence | URL · manifest | adapter |
|---|---|---|---|---|---|---|---|---|
| WPB | `~/wpb` | fresh translation: wpb-mt (WLC), wpb-lxx (Swete), wpb-nt (SBLGNT), reader's wprb; notes, lemmas, MT–LXX alignment | `ref`, OSIS (`1Sam.1.1`); `id` `wpb-mt:1Sam.1.1`; Swete letters `Gen.1.24a` | partial: 14 OT books (MT 7,171 v., LXX 7,126), 19 NT books (7,090 v.) | per chapter: `mt`, `lxx`, `nt`; `maps_to` on 1,024 MT and 7,111 LXX verses | English, notes, encoding CC BY 4.0; Swete-inlined layers CC BY-SA 4.0 (`SOURCES.md`) | bible.wrootpress.com · `/api/index.json` | **versification**: MT→KJV through `maps_to` (Mal 3:19–24, psalm titles); LXX keeps its own |
| Fons | `~/fons` | the shared WEB text the lenses fetch | path `web/<slug>/<ch>.json` + `v`; OSIS built by `client/fons.ts` | 66 books, 31,095 v.; deuterocanon only 319 cited verses | KJV/WEB (stated in manifest) | WEB public domain; deuterocanon source undocumented | fons.wrootpress.com · `/web/_manifest.json` | none (its client emits OSIS); deuterocanon keyed by English strings |
| Verbum | `~/verbum` | sound lens: Hebrew wordplay | `refKey` OSIS in `/index.json`; Hebrew layer `"1.1"` per book | 19 plays (Gen 13, Amos 6); Hebrew for 6 books | index KJV/WEB; Hebrew MT | own work CC BY-NC 4.0, ML training allowed; OSHB CC BY 4.0 | verbum.wrootpress.com · `/index.json` (the PLAN's model manifest) | none for the index; the MT Hebrew diverges in 1 Kgs 4–5 |
| Topographia Sacra | `~/topographia-sacra` | place lens: verses with places mapped (ABD identifications) | **no key**: slug + chapter file + `n`; places by slug | 5 whole books: Josh, Judg, Ruth, Jonah, Acts (2,416 v., 867 tagged); 548 places | not stated; data English (Jonah 1 = 17 v., Acts 8:37) | own work CC BY-NC 4.0 | topographia.wrootpress.com · `data/books.json` only | **build key** `{OSIS(slug)}.{ch}.{n}` |
| Loci | `~/loci` | theme lens: pericopes tagged by theme | **no key**: human `ref` `"6:14–23"`, book implicit in file | 8 OT books whole (Chr, Ezek, Lev, Num, Eccl, Lam, Song), 5,677 v. | not stated; data English (Lev 6:1–30) | CC BY-NC 4.0 (LICENSE) | no domain in files · none | **parse** ranges; Chronicles `ch` runs 1–65 (2 Chr offset 29): read book from `ref` |
| Catena | `~/catena` | connections lens: NT use of the OT, typed and scored | `refKey` OSIS, mostly ranges | NT side 7,864 v. (27 books); OT side ~7,141 v. (60 book codes incl. deuterocanon, 1En, Jub) | KJV/WEB (stated) | open data CC BY-SA 4.0 (`public/data/LICENSE.txt`) | catena.wrootpress.com · `/data/manifest.json` (snapshot 2026-07-01, may lag `data/`) | none; join on range overlap |
| Annales Sacra | `~/annales-sacra` | time lens: reigns, journeys (Thiele), a gospel harmony | **no key**: human strings (`"1 Kings 12:20–14:20"`), some chapter-only or labels; records keyed by year | sparse spans: Kings, Chr, Acts, Paul, 4 Gospels | not stated; WEB through Fons | CC BY-NC 4.0 (LICENSE) | annales.wrootpress.com · none | **parse**; spans are reigns, not verses |
| Voces | `~/voces` | voice lens: who speaks each passage | **no key**: `Unit.ref` human ranges (`"Psalms 2:7–9"`, "Song" alias) | 212 units, ~1,614 v.; Job and Song whole | not stated; WEB | CC BY-NC 4.0 (LICENSE) | voces.wrootpress.com · none | **parse**; the Torah edition's `book` says Genesis but holds Exod and Deut |

## 2. Witness: how it reached us

| layer | repo | holds | key as stored | coverage | versification | licence | URL · manifest | adapter |
|---|---|---|---|---|---|---|---|---|
| Paleography | `~/paleography` | line-level HTR ground truth, 9 witnesses (Latin, Greek, Syriac, Old French) | **not verse-keyed**: (`witness`, `page`, `line_id`) | 27,183 lines (stated); Syriac Gospels (2,868 lines) and an Irish Matthew commentary (7,889) carry no verse field | n/a | per dataset (`corpus/sources.yml`); wien940 and onb-syr1 **contested** BY vs BY-SA | paleography.app · `build/payload/index.json` | a verse join needs a new line→verse alignment |
| migne.app scripture index | `~/patrologia` (`data/index/`) | Migne's own scripture notes, by work and column | `refKey` OSIS + `refDisplay` + `column` | 187 works, 11,463 records; **80% chapter-only**; 1,535 verse-level keys | **Vulgate** (Ps 118 cited 85 times, Ps 119 16) | Latin PD; English and "structure, keys, anchors" CC BY-NC 4.0 | migne.app · `export/manifest.json` | **versification**: OSIS names on Vulgate numbers |
| Kraken Greek OCR | `~/patrologia/htr` | raw PG OCR and models | not verse-keyed: `<work>/p-NNNN`, PG vol + column | 7 works, 729 pages | n/a | CLLG base model CC BY 4.0 | none | n/a (feeds the PG track, PLAN G) |
| Douay + Glossa | `~/douay-glossa` | Douay-Rheims verse text with the Glossa ordinaria English per verse | Latin slug file (`liber-iii-regum`) + integer chapter/verse; glosses `verse_start`/`verse_end` | 56 books, 31,322 v.; 14,991 glossed; missing Lam, Ezek, Dan, the Twelve, 1–2 Macc | **Vulgate/Douay** (stated: "Ps 23 = Hebrew Ps 24") | DRC, Clementine PD; Glossa English CC BY-NC 4.0 (patrologia) | glossa.wrootpress.com · `data/index.json` | **slug map + versification**; de-duplicate the 1,884 range glosses |
| Lyra *Postilla* | `~/lyra-postilla` | planned: OCR and English of the Venice 1603 *Postilla* | none yet (planned book/chapter + `verse_start`/`verse_end` + `col`) | 0: "SKETCH. Nothing built" | planned Clementine Vulgate | none yet; Gloss-e transcription is consult-only | lyra.wrootpress.com (working name) | n/a until built |
| KJV + Wesley's *Notes* | `~/kjv-wesley` | KJV text and Wesley's *Explanatory Notes* | slug + integer chapter/verse; notes `verse_start`/`verse_end` | 66 books; 31,102 v. after the 2026-11-10 repair (was 31,100); notes on 17,857 v. | KJV (inferred) | CCEL Wesley and the KJV JSON PD (README) | notes.historyofmethodism.com · `web/data/{kjv,notes}/index.json` | **slug map**; KJV repaired 2026-11-10 (flags) |

## 3. Reception: what readers did with it

| layer | repo | holds | key as stored | coverage | versification | licence | URL · manifest | adapter |
|---|---|---|---|---|---|---|---|---|
| Reception corpus | `~/reception-corpus` | the shared "what has the church said here" store behind Lectern: 9 sources (JFB 32,281 rows; Catena 18,495; Wesley 17,920; Calvin 14,052; Glossa 13,733; Barnes 8,207; Henry 5,569; Catena Aurea 4,829; Barth pointers 724) | `refKey` OSIS + integer `book/chapter/v_start/v_end` | **115,810 rows** (README stale at 101,353); ~34,558 v.; 85 books | KJV/WEB (stated; RCL normalized from NRSV) | per row: view `reception_licensed` (PD 82,858; Catena CC BY-SA 18,495; Glossa CC BY-NC 13,733; Barth pointer 724); compilation CC BY-NC 4.0 | none (internal) | none; join on overlap columns. **This is the hub** |
| Bereshit | `~/bereshit` | Latin and rabbinic reading of Gen 1:1–5: 292 witnesses, 10 cruxes, 456 threads | `anchor.verse` lowercase `gen.1.1` | 5 verses | n/a (identical across schemes here) | own work CC BY 4.0, ML allowed; Sefaria CC BY-SA per witness | bereshit.wrootpress.com · `export/manifest.json` | **case** only |
| Talmai | `~/surplus` | Esther LXX–MT pluses against Jewish reception | `"Esther 1:1"`; Greek Additions `1:1a` (Rahlfs), CATSS and Swete refs kept | Esther, 167 v. | MT/Sefaria; Additions Rahlfs | English CC BY 4.0, Swete CC BY-SA (`llms.txt`); no LICENSE | talmai.wrootpress.com · `site/public/data/manifest.json` | **parse**; never collapse `1:1a` to `1:1`. Repo private until Wilson rules (`PHASES.md`) |
| Brass | `~/bible-in-bom` | KJV quotations and echoes in the Book of Mormon | BoM side slug + `"1:1"`; Bible side `"Exodus 2:2"`, `"Psalm"` singular | 2,390 KJV verses cited, 63 books | KJV | CC BY-NC 4.0 (LICENSE, Wilson 2026-09-10); the 1830 transcription declares no licence (blocks publication) | brass.wrootpress.com · none | **parse**; the Bible verse is the *cited* text |
| Liber generationis | `~/liber-generationis` | the genealogies of Jesus: people, questions, readers' answers | **not verse-keyed**: person id / question slug; refs `"1Chr 3:1-19"` | 426 refs (253 ranges), ~1,511 v. | not stated; WEB | CC BY-NC 4.0 (LICENSE) | ntnames.wrootpress.com/genealogies/ · none | **parse** + abbreviation map; local only, no remote |
| Named in Acts and the Letters | `~/nt-prosopography` | every person named Acts–Jude, by verse | eBible codes `"ACT 1:13"`, `PHI`, `JAM` | 169 people, 466 v., 20 books | not stated; WEB | CC BY-NC 4.0 (LICENSE); repo public | ntnames.wrootpress.com · none | **code map** (eBible ≠ USFM ≠ OSIS) |
| sensus claims ledger | `~/scriptura/studies/sensus` | de Lubac's footnotes coded (17,041 rows); the PL sense-term census | PL vol + column; scripture as free text | whole *Exégèse médiévale*; 87.1M PL words | mixed: de Lubac cites the Vulgate, and the reader sometimes converted (`Ps.119.66` for Vulg. 118:66). Field is OSIS but the scheme is per row unknown | **in copyright: pointer-only, never published**; census derived from PD Latin | none | the scripture field needs the stage C spine before it can join |
| Latin corpus | `~/latin-lm` | the clean Christian-Latin training corpus | by document, not verse | 123.2M words (PL 76.6M, Acta 43.6M, Bonaventure 2.31M, Vulgate 0.60M) | n/a | PL and Acta **not cleared**: local only | none (publishing is a hard stop) | n/a |
| Abstracting the Bible | `~/abstracting-the-bible` | a scoping note for scripture on objects | none (planned OSIS `ref`) | 0 | planned per object | n/a | none | n/a until built |

## 4. What blocks the join

**Keys.** Five key forms are in use besides OSIS:
- lowercase OSIS (bereshit)
- English names with `c:v` (Talmai, Brass, Loci, Annales, Voces)
- SBL-style abbreviations (Liber generationis)
- eBible codes (Named in Acts)
- slug + integers (Topographia, Douay-Glossa, KJV-Wesley)

One normalizer (string or slug → OSIS, with ranges) covers all of them.

**Versification.** Four schemes:
- **KJV/WEB**: the standard
- **MT**: WPB-mt; Verbum's Hebrew
- **LXX/Swete or Rahlfs**: WPB-lxx; the Esther Additions
- **Vulgate**: migne.app; Douay-Glossa; the sensus ledger; Lyra and the Latin census to come

The Vulgate crosswalk (Psalms 9–147, the four books of Kings, Sirach) matters most to Scriptura, since the whole Latin reception layer is numbered that way. WPB's `maps_to` is the only crosswalk that exists, and only for its own verses.

**Flags found in the survey:**
- ✅ **KJV-Wesley's KJV was damaged; repaired 2026-11-10** (was 31,100 verses; also four split verses rejoined). The damaged chapters are Matt 2, 22, 26 and
  Mark 4, 7, 8: each loses one verse, and the verses after it are renumbered. The damage is in the
  **text array only**. Wesley's notes carry their own correct verse numbers (checked: Matt 2:23,
  22:46, 26:74), so reception-corpus's 17,920 Wesley rows are sound. The crosswalk below uses the
  WEB for Matthew and Mark.
- reception-corpus's README is stale (101,353 stated against 115,810 rows).
- Licences: Loci, Annales, Brass and reception-corpus already carried CC BY-NC 4.0 on GitHub (Wilson, 2026-09-10); the survey read stale local clones and missed it. Wilson 2026-11-10: keep BY-NC, the house rule, for every annotation layer. Named in Acts, Voces and Liber generationis now match. reception-corpus has per-row licences (Catena rows stay BY-SA, inbound). ⚠ BY-NC (Verbum, Topographia, migne keys, Glossa) and BY-SA (Catena, Swete) cannot merge into one adapted dataset: joined exports ship per-licence files. Paleography has two contested datasets.
- Repo visibility is stated only for nt-prosopography, paleography, patrologia and kjv-wesley (public) and Talmai (private). Voces, Douay-Glossa and Liber generationis have no remote at all.
- migne.app: 80% of the scripture index is chapter-only.

## 5. Tools (built 2026-11-10, no tokens)

- **`tools/refkey.py`** turns every key form in section 4 into the OSIS refKey: `parse()`,
  `parse_many()` and `book()`. It handles Latin abbreviations as Migne and de Lubac print them,
  with Roman chapters, chapter lists ("Gen. XXI, XXII"), verse lists ("XIII, 6, 21"), "et"
  lists, "seq.", "III Reg." and French. Versification is never guessed: the caller states it.
  - Self-test: 65 format cases and 8 crosswalk cases (`python3 -I tools/refkey.py`).
  - Measured on the layers' own data: Brass, Named in Acts, Talmai, Voces and Loci 100%;
    Annales 95% (the rest are labels such as "Philippi · Thessalonica"); migne.app's printed
    Latin 9,954 of 10,393 that are not ibid. (95.8%; the 1,070 ibid./idem need their context).
- **`tools/build_crosswalk.py` → `data/crosswalk-vulg-kjv.tsv`**: Vulgate to KJV, verse by
  verse, 37,000 rows (`same` 27,876; `moved` 2,928; `split` 94; `merge` 159; `title` 67;
  `vulg-only` 6,131, which is the deuterocanon plus the Greek parts of Daniel and Esther;
  `kjv-only` 34). How it was built:
  - Derived, not hand-typed: the Douay-Rheims (exactly the Clementine numbering) aligned to
    the KJV (the WEB for Matthew and Mark).
  - A second pass pairs the Vulgate's swapped verses (Matt 5:4–5, 23:13–14, Phil 1:16–17).
  - 19 known boundaries are asserted on every build: Psalms 9/10, 22/23, 50/51, 118/119 and
    147, Daniel 3, Job 40/41, John 6:52, Mark 8:39 and 3 John 15.
  - `refkey.to_kjv()` applies it.
  - Low-score pairs (327, mostly genealogies and name lists) and the 34 `kjv-only` rows are
    where to look first if a join looks wrong.

## 6. Next

1. **The citation spine** (PLAN stage C, the `canon` Study): the PL's scripture citations,
   `refKey` × author × work × column. migne.app's 11,463 index records convert now with
   `refkey` + `to_kjv`. The rest of the PL needs the detector against the Clementine.
2. ✅ KJV-Wesley text repaired in that repo (2026-11-10, `scripts/repair_kjv.py`).
3. Each row is re-read from the repo when its layer changes. The registry is not updated from
   memory.
