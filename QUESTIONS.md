# Scriptura — the register of questions

Written 2026-11-09. `PLAN.md` is the score; this file is the queue it points to. **One at a time,
in order.** Order ruled by Wilson 2026-11-10: sensus → canon → questions → divisions → nameless. A question becomes a Study when
it gets `studies/<slug>/STUDY.md` (form in `PLAN.md` section 4).

Chosen by Wilson 2026-11-09: the de Lubac study, plus the four below. The numbers in brackets are
the numbers the questions carried in the planning conversation.

---

## The queue

### 1. `sensus` — de Lubac's four senses, counted
Fully specified in `PLAN.md` section 5. Its stage C is the first stage of `canon`.

### 2. `canon` — the working canon [1]

**Question.** Which verses did each tradition actually use, and which did nobody touch?

- **Layer produced:** the citation spine, `refKey` × author × work × locus. Everything on the
  Reception side joins to it.
- **Stage 1, PL:** the detector run described in `PLAN.md` stage C (Clementine Vulgate, three
  streams on the Brass model, adjudication). Mind the Old Latin and the Psalm numbering.
- **Then, in this order:** Bonaventure (a citation ledger already exists in
  `~/bonaventure-sentences`); the Acta; Wesley; the Revised Common Lectionary (1,188 readings
  already in `~/reception-corpus`); the rabbinic bench used by Bereshit and Talmai; the PG as
  Kraken delivers it.
- **Findings to look for:** verses never cited in a thousand years of Latin; verses one tradition
  leans on and another ignores; what each author's working Bible looks like against the whole.
- **A by-product, free once the spine exists:** which verses are habitually cited together
  (question 3 in the set-aside list). Note it; do not build it unasked.
- **Pastoral turn:** the Bible a congregation never hears. For each Sunday, Lectern can show what
  the lectionary leaves out that the Fathers leaned on.

### 3. `questions` — the questions of the Bible [6]

**Question.** Every question in Scripture: who asks whom, what kind of question is it, and is it
answered?

- **Computation first:** candidate questions from the Hebrew interrogatives (WLC morphology) and
  from the question marks in the Greek. The Greek punctuation is an editor's, so treat it as a
  candidate list, not as fact.
- **Codebook:** asker; addressee; kind (asks for information, accuses, laments, rhetorical);
  answered or not; by whom; how far away the answer is.
- **Leans on:** the speaker layer in `~/voces`.
- **Scale:** the whole Bible is one small pass. This is the cheapest Study to run from end to end,
  and a good first test of the Study form if Wilson wants a finished one early.
- **Findings to look for:** God's questions to people; Jesus's questions; the questions left
  hanging; who is never allowed to ask.
- **Pastoral turn:** a sermon series nearly ready-made, and a per-Sunday note in Lectern.

### 4. `divisions` — who cut the text where [9]

**Question.** The text has been divided many times, by people with different purposes. Where do
the divisions agree, and where does a break mislead the reader?

- **Layers to assemble:** the Masoretic open and closed paragraphs; the ancient Greek chapter
  divisions and the Eusebian canons; Langton's chapters; Estienne's verses; the lectionary's cuts
  (from `~/reception-corpus`); paragraphing in the public-domain editions. Optional comparison
  layer: a model's own discourse segmentation.
- ⬜ **Verify before scoping:** that the Masoretic paragraph marks are in the WLC files on disk, and
  that open, rights-clear data exists for the Greek divisions and the canons.
- **Mostly computation.** A model reads only at the disputed breaks.
- **Findings to look for:** chapter breaks that fall mid-thought; places where every ancient
  division disagrees with the printed one; where the lectionary cuts against all of them.
- **Pastoral turn:** a warning in Lectern when a reading starts or stops at a misleading break.
- **Witness-layer link:** the divisions are visible on the page, so this is the Study that puts
  biblical manuscripts in front of paleography.app's learners.

### 5. `nameless` — who named the nameless [5]

**Question.** Scripture leaves many people unnamed, and tradition later supplied names (Dismas,
Longinus). Who named them, when, and where did the names travel?

- **Stage 1:** the list of unnamed figures, from a pass over the biblical text.
- **Stage 2:** search the Acta, the PL, and later sources for supplied names. Every name needs a
  located source; nothing is attributed from recall.
- **Leans on:** `~/nt-prosopography`, `~/liber-generationis`, the Acta saint pages, and the
  `canon` spine for finding where a verse is discussed.
- **Record:** evidence-tagged, first attestation dated, competing names kept side by side.
- **Pastoral turn:** a sermon on the unnamed, and a note on the people page of the prosopography.

---

## Set aside 2026-11-09 (not queued; kept so they are not re-invented)

- **[3] Verses that travel together.** Co-citation pairs. Falls out of the `canon` spine.
- **[4] Which Bible was he quoting?** Fingerprinting the version behind a quotation. (2026-11-10:
  the spine measured the gap: Clementine matching finds 29% of Migne's verse citations for Fathers
  d.≤400 against ~50% after 600, in `studies/canon/STUDY.md`. The canon fuzzy stream builds
  most of this. Still set aside.)
- **[7] Does God stop talking?** Divine direct speech across the canon; partly answerable from
  the `questions` speaker coding.
- **[8] Where translators can't agree.** Per-verse variance across versions against commentary
  density.
- **[10] Do reading errors predict variants?** The learner and HTR confusion table against
  attested variants. Needs open variant data.
