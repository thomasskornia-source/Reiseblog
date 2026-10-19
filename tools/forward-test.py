#!/usr/bin/env python3
"""Fortlaufender Test (Thomas, 20.10.2026) -> data/forward.json

Jeden Handelstag wird der WCJ-Score aller S&P-500-Aktien (aus data/universum.json, das top10.yml täglich schreibt) samt Schlusskurs festgehalten.
Später wird gemessen, was nach 5, 20 und 60 Handelstagen daraus geworden ist: mittlere Rendite je Stufe, Rangkorrelation (IC) und Abstand Stark minus Schwach.
Das ist die ehrliche Gegenprobe: Der Score wurde VOR der Rendite festgehalten, nichts wird zurückgerechnet.
Archiv: je Datum {Kürzel: [Punkte, Kurs]}, höchstens 130 Handelstage. Beginnt mit dem ersten Lauf.
"""
import datetime, json, math, os
ROOT = os.path.join(os.path.dirname(__file__), '..')
UNI = os.path.join(ROOT, 'data', 'universum.json')
PFAD = os.path.join(ROOT, 'data', 'forward.json')
HOR = (5, 20, 60)
MAXTAGE = 130
STUFEN = [('Stark', 8), ('Momentum', 6), ('Beobachten', 4), ('Schwach', 0)]

def iso(d):
    t, m, j = d.split('.'); return '%s-%s-%s' % (j, m, t)

def stufe(p):
    for n, g in STUFEN:
        if p >= g: return n

def rang(v):
    o = sorted(range(len(v)), key=lambda i: v[i]); r = [0.0] * len(v); i = 0
    while i < len(o):
        j = i
        while j + 1 < len(o) and v[o[j + 1]] == v[o[i]]: j += 1
        for k in range(i, j + 1): r[o[k]] = (i + j) / 2
        i = j + 1
    return r

def pearson(a, b):
    n = len(a)
    if n < 10: return None
    ma, mb = sum(a) / n, sum(b) / n
    sa = math.sqrt(sum((x - ma) ** 2 for x in a)); sb = math.sqrt(sum((x - mb) ** 2 for x in b))
    return sum((x - ma) * (y - mb) for x, y in zip(a, b)) / (sa * sb) if sa and sb else None

def main():
    u = json.load(open(UNI, encoding='utf-8'))
    tag = iso(u['stand']) if '.' in u['stand'] else u['stand']
    try: alt = json.load(open(PFAD, encoding='utf-8'))
    except Exception: alt = {}
    arch = alt.get('archiv', {})
    arch[tag] = {a['t']: [a['p'], a['k']] for a in u['aktien'] if a.get('p') is not None and a.get('k')}
    for d in sorted(arch)[:-MAXTAGE]: del arch[d]
    tage = sorted(arch)
    out_h = {}
    for h in HOR:
        je_stufe = {n: [] for n, _ in STUFEN}; ics = []; alle = []
        for i, d in enumerate(tage):
            if i + h >= len(tage): break
            d2 = tage[i + h]; ps, rs = [], []
            for t, (p, k) in arch[d].items():
                if t not in arch[d2] or not k: continue
                r = (arch[d2][t][1] / k - 1) * 100
                je_stufe[stufe(p)].append(r); ps.append(p); rs.append(r); alle.append(r)
            c = pearson(rang(ps), rang(rs)) if len(ps) > 30 else None
            if c is not None: ics.append(c)
        if not alle: out_h[str(h)] = None; continue
        mw = lambda v: round(sum(v) / len(v), 2) if v else None
        base = mw(alle)
        ic = round(sum(ics) / len(ics), 3) if ics else None
        t = None
        if len(ics) > 3:
            m = sum(ics) / len(ics); sd = math.sqrt(sum((x - m) ** 2 for x in ics) / (len(ics) - 1))
            n_eff = max(1, len(ics) / h)       # überlappende Zeiträume
            t = round(m / (sd / math.sqrt(n_eff)), 2) if sd else None
        out_h[str(h)] = {'tage': len(ics), 'beobachtungen': len(alle), 'grundrate': base, 'ic': ic, 't': t,
                         'stufen': {n: {'n': len(v), 'rendite': mw(v)} for n, v in je_stufe.items()},
                         'stark_minus_schwach': round(mw(je_stufe['Stark']) - mw(je_stufe['Schwach']), 2) if je_stufe['Stark'] and je_stufe['Schwach'] else None}
    out = {'stand': tag, 'seit': tage[0], 'handelstage': len(tage), 'horizonte': out_h,
           'hinweis': 'Score wird täglich vor der Rendite festgehalten, nichts wird zurückgerechnet. Unter 20 Handelstagen Archiv sagt der Test noch nichts; belastbar frühestens nach einigen Monaten.',
           'archiv': arch}
    with open(PFAD, 'w', encoding='utf-8') as fh:
        fh.write(json.dumps(out, ensure_ascii=False, separators=(',', ':')) + '\n')
    print('Archiv', len(tage), 'Tage; Horizonte', {h: (v or {}).get('beobachtungen') for h, v in out_h.items()})

if __name__ == '__main__':
    main()
