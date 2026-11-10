#!/usr/bin/env python3
"""Stage D, first pass: read the 269 stated formulas found by the census (census/formulas.tsv).

  python3 -I scripts/formulas_read.py prep                    # no tokens: inputs with wider Latin context
  uv run -q --with anthropic python -I scripts/formulas_read.py count        # free: exact input tokens
  uv run -q --with anthropic python -I scripts/formulas_read.py submit A [ids-file]   # Batch, Opus high
  uv run -q --with anthropic python -I scripts/formulas_read.py fetch [batch_id ...]
  python3 -I scripts/formulas_read.py agree A B               # blind agreement, no tokens

Each formula goes to the model with its author, death year, work, PL column, and about 1,800
characters of Latin around the hit (PL text, public domain). The model says what the passage is
doing with the senses, under codebook F1 below. Output: working/formulas/<coder>/<id>.json, then
ledger/formulas-coded.tsv.
"""
import collections, csv, glob, html, json, os, random, re, subprocess, sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEI = os.path.expanduser('~/patrologia/sources/pl/tei')
W = os.path.join(HERE, 'working', 'formulas')
MODEL, EFFORT, CODEBOOK = 'claude-opus-5-5', 'high', 'F1 2026-11-10'
CTX = 900

SYSTEM = """You are reading passages from the Patrologia Latina for a study of the senses of scripture
(after Henri de Lubac, Exégèse médiévale). A word census flagged each passage because three or more
sense terms (historia, littera, allegoria, mystice, typice, tropologia, moraliter, anagoge...) occur
within 60 words. Your job: say what the passage is actually doing with the senses. Read the Latin
closely; the hit is in the middle of the excerpt, which may begin and end mid-sentence.

Codebook F1:

kind — exactly one:
  theory       the passage states, defines or argues for a scheme of senses (how many there are,
               what each is, how they relate). "Quattuor sunt regulae Scripturae..." is theory.
  application  it reads one particular text of scripture under several senses in turn
               ("secundum historiam... allegorice... moraliter...") without stating the scheme.
  list         it names several senses in passing (a preface promising to treat a book "historice,
               allegorice et moraliter", a title, a cross-reference), neither defining nor applying.
  quotation    it reproduces another author's statement of the senses (say whose in authority).
  other        the terms are not about senses of scripture here (false positive), or the text is
               too damaged to tell.

senses — the senses the passage names, in the order it names them, as the source's own Latin
  words in dictionary form (e.g. ["historia", "allegoria", "tropologia", "anagoge"]). Record every
  sense term, including near-synonyms (mystice, spiritualiter, moraliter, sensus litteralis).
mapped — the same list, same order, each mapped to: letter | allegory | tropology | anagogy |
  spiritual (a generic "spiritual sense" not further specified) | other.
count_stated — if the passage says how many senses there are ("quattuor", "triplex", "septem"),
  that number as a string; else "".
definitions — for each sense the passage DEFINES (not merely names): term (Latin), gloss (our
  words, English, at most 20), latin (the defining phrase as printed, at most 15 words).
example — the scripture text or figure used to illustrate the senses, if any: osis (e.g.
  "Gal.4.24", "" if none or unclear) and figure (e.g. "Jerusalem", "Sara et Agar", "").
authority — the author the passage invokes for its scheme ("Gregorius", "Cassianus", "Beda",
  "Hieronymus", "Origenes"...), or "".
summary — at most 40 words, English, our words: what the passage says about the senses.
confidence — high | medium | low.

Use "" for an empty string field and [] for an empty list. Do not invent: if the excerpt is cut off
before a definition, record only what is there."""

S = {'type': 'string'}
SCHEMA = {'type': 'object', 'additionalProperties': False,
          'required': ['kind', 'senses', 'mapped', 'count_stated', 'definitions', 'example', 'authority', 'summary', 'confidence'],
          'properties': {
              'kind': {'type': 'string', 'enum': ['theory', 'application', 'list', 'quotation', 'other']},
              'senses': {'type': 'array', 'items': S},
              'mapped': {'type': 'array', 'items': {'type': 'string', 'enum': ['letter', 'allegory', 'tropology', 'anagogy', 'spiritual', 'other']}},
              'count_stated': S,
              'definitions': {'type': 'array', 'items': {'type': 'object', 'additionalProperties': False,
                              'required': ['term', 'gloss', 'latin'], 'properties': {'term': S, 'gloss': S, 'latin': S}}},
              'example': {'type': 'object', 'additionalProperties': False, 'required': ['osis', 'figure'],
                          'properties': {'osis': S, 'figure': S}},
              'authority': S, 'summary': S,
              'confidence': {'type': 'string', 'enum': ['high', 'medium', 'low']}}}

def norm(s):
    return s.lower().replace('j', 'i').replace('v', 'u')

def clean_text(f):
    """The same pipeline as census.py's one(), without the lower-casing, so offsets agree."""
    raw = open(f, encoding='utf-8', errors='replace').read()
    body = raw[raw.find('<text'):] if '<text' in raw else raw
    body = re.sub(r'<pb\s+n="0*(\d+)([A-D]?)"\s*/?>', lambda m: f' \x01{m.group(1)}{m.group(2)}\x01 ', body)
    body = html.unescape(re.sub(r'<[^>]+>', ' ', body))
    parts = re.split(r'\x01([^\x01]*)\x01', body)
    return ''.join(re.sub(r'\s+', ' ', p) for k, p in enumerate(parts) if k % 2 == 0)

def prep():
    rows = list(csv.DictReader(open(os.path.join(HERE, 'census', 'formulas.tsv'), encoding='utf-8'), delimiter='\t'))
    os.makedirs(W, exist_ok=True)
    out, miss, cache = [], 0, {}
    for k, r in enumerate(rows, 1):
        fid = f'F{k:03d}'
        if r['idno'] not in cache:
            cache.clear(); cache[r['idno']] = clean_text(os.path.join(TEI, r['idno'] + '.xml'))
        t = cache[r['idno']]
        i = norm(t).find(r['snippet'][:120])
        if i < 0:
            miss += 1; ctx = r['snippet']
        else:
            a, b = max(0, i - CTX + 200), min(len(t), i + len(r['snippet']) + CTX - 200)
            ctx = ('…' if a else '') + t[a:b].strip() + ('…' if b < len(t) else '')
        out.append({'id': fid, **{x: r[x] for x in ('idno', 'vol', 'col', 'author', 'author_year', 'century', 'title', 'families', 'terms')},
                    'context': ctx})
    with open(os.path.join(W, 'inputs.jsonl'), 'w', encoding='utf-8') as f:
        for o in out:
            f.write(json.dumps(o, ensure_ascii=False) + '\n')
    print(len(out), 'inputs; context not re-found (snippet used):', miss, '; mean chars', sum(len(o['context']) for o in out) // len(out))

def inputs():
    return [json.loads(l) for l in open(os.path.join(W, 'inputs.jsonl'), encoding='utf-8')]

def user_msg(o):
    d = f"d. {o['author_year']}" if o['author_year'] not in ('', '0') else 'date unknown'
    return (f"Author (as the PL prints it): {o['author']} ({d})\nWork: {o['title']}\nPL {o['vol']}, col. {o['col']}\n"
            f"Census hit: senses {o['families']} (L letter, A allegory, T tropology, N anagogy); terms {o['terms']}\n\n"
            f"Latin excerpt:\n{o['context']}")

def client():
    import anthropic
    key = subprocess.run(['security', 'find-generic-password', '-s', 'anthropic-api', '-w'],
                         capture_output=True, text=True, check=True).stdout.strip()
    return anthropic.Anthropic(api_key=key, max_retries=4)

def count():
    c, tot = client(), 0
    for o in inputs():
        tot += c.messages.count_tokens(model=MODEL, system=SYSTEM, messages=[{'role': 'user', 'content': user_msg(o)}]).input_tokens
    n = len(inputs())
    print(f'{n} requests, {tot:,} input tokens ({tot // n:,} each)')

def submit(coder, ids_file=None):
    want = set(open(ids_file).read().split()) if ids_file else None
    os.makedirs(os.path.join(W, coder), exist_ok=True)
    reqs = [{'custom_id': f'{coder}-{o["id"]}', 'params': {
        'model': MODEL, 'max_tokens': 16000, 'system': SYSTEM,
        'output_config': {'effort': EFFORT, 'format': {'type': 'json_schema', 'schema': SCHEMA}},
        'messages': [{'role': 'user', 'content': user_msg(o)}]}}
        for o in inputs() if (want is None or o['id'] in want) and not os.path.exists(os.path.join(W, coder, o['id'] + '.json'))]
    if not reqs:
        print('nothing to submit'); return
    b = client().messages.batches.create(requests=reqs)
    with open(os.path.join(W, 'batches.tsv'), 'a') as f:
        f.write('\t'.join([b.id, coder, MODEL, EFFORT, CODEBOOK, str(len(reqs))]) + '\n')
    print(b.id, b.processing_status, len(reqs), 'requests')

def fetch(ids):
    c = client()
    rows = [l.rstrip('\n').split('\t') for l in open(os.path.join(W, 'batches.tsv'))]
    for bid, coder, model, *_ in rows:
        if ids and bid not in ids:
            continue
        b = c.messages.batches.retrieve(bid)
        print(bid, coder, b.processing_status, b.request_counts)
        if b.processing_status != 'ended':
            continue
        tin = tout = 0; bad = []
        for r in c.messages.batches.results(bid):
            fid = r.custom_id.split('-', 1)[1]
            if r.result.type != 'succeeded':
                bad.append((fid, r.result.type)); continue
            m = r.result.message
            text = ''.join(x.text for x in m.content if x.type == 'text')
            try:
                data = json.loads(text)
            except json.JSONDecodeError:
                data = None
            if m.stop_reason != 'end_turn' or data is None:
                bad.append((fid, m.stop_reason))
            tin += m.usage.input_tokens; tout += m.usage.output_tokens
            json.dump({'id': fid, 'coder': coder, 'model': model, 'codebook': CODEBOOK, 'batch': bid, 'stop': m.stop_reason,
                       'input': m.usage.input_tokens, 'output': m.usage.output_tokens, 'data': data, 'raw_text': None if data else text},
                      open(os.path.join(W, coder, fid + '.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        print(json.dumps({'batch': bid, 'input': tin, 'output': tout, 'usd_batch': round((tin * 4 + tout * 20) / 2e6, 2), 'problems': bad}))

def load(coder):
    return {os.path.basename(f)[:-5]: json.load(open(f, encoding='utf-8'))['data'] for f in glob.glob(os.path.join(W, coder, 'F*.json'))}

def agree(A, B):
    a, b = load(A), load(B)
    ids = sorted(i for i in set(a) & set(b) if a[i] and b[i])
    def kappa(pairs):
        n = len(pairs); po = sum(x == y for x, y in pairs) / n
        ca, cb = collections.Counter(x for x, _ in pairs), collections.Counter(y for _, y in pairs)
        pe = sum(ca[k] * cb[k] for k in ca) / n / n
        return (po - pe) / (1 - pe) if pe < 1 else 1.0
    kp = [(a[i]['kind'], b[i]['kind']) for i in ids]
    lines = [f'# Formulas: coder {A} vs {B}', '', f'{len(ids)} passages coded by both.', '',
             f"kind: agree {sum(x == y for x, y in kp)}/{len(ids)}, kappa {kappa(kp):.2f}",
             f"mapped senses (same list, same order): {sum(a[i]['mapped'] == b[i]['mapped'] for i in ids)}/{len(ids)}",
             f"mapped senses (same set): {sum(set(a[i]['mapped']) == set(b[i]['mapped']) for i in ids)}/{len(ids)}",
             f"count_stated: {sum(a[i]['count_stated'] == b[i]['count_stated'] for i in ids)}/{len(ids)}",
             f"authority (same first word, case-folded): {sum(a[i]['authority'].lower().split()[:1] == b[i]['authority'].lower().split()[:1] for i in ids)}/{len(ids)}",
             '', '| A \\ B | ' + ' | '.join(['theory', 'application', 'list', 'quotation', 'other']) + ' |', '|---' * 6 + '|']
    cm = collections.Counter(kp)
    for x in ['theory', 'application', 'list', 'quotation', 'other']:
        lines.append(f'| {x} | ' + ' | '.join(str(cm[(x, y)]) for y in ['theory', 'application', 'list', 'quotation', 'other']) + ' |')
    open(os.path.join(W, f'agreement-{A}{B}.md'), 'w').write('\n'.join(lines) + '\n')
    with open(os.path.join(W, f'disagreements-{A}{B}.tsv'), 'w', encoding='utf-8') as f:
        f.write('id\tfield\tA\tB\n')
        for i in ids:
            for fld in ('kind', 'mapped', 'count_stated', 'authority'):
                if a[i][fld] != b[i][fld]:
                    f.write(f"{i}\t{fld}\t{json.dumps(a[i][fld], ensure_ascii=False)}\t{json.dumps(b[i][fld], ensure_ascii=False)}\n")
    print('\n'.join(lines))

if __name__ == '__main__':
    cmd = sys.argv[1]
    if cmd == 'prep': prep()
    elif cmd == 'count': count()
    elif cmd == 'submit': submit(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else None)
    elif cmd == 'fetch': fetch(sys.argv[2:])
    elif cmd == 'agree': agree(sys.argv[2], sys.argv[3])
