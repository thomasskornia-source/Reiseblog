#!/usr/bin/env python3
"""Sektor-Optionsfluss (Thomas, 15.10.2026, nach Screenshots einer fremden Sektor-Seite) -> data/sektorflow.json, Seite sektorfluss.html.

Aufruf:  python3 tools/sektorflow.py          läuft werktags nach US-Börsenschluss (sektorflow.yml)
Quelle: verzögerte Optionsdaten der Cboe (wie tools/optionsfluesse.py), alle S&P-500-Aktien plus ein paar ETFs.
Gezählt wird je Aktie und Tag, welche Kontrakte „auffällig“ waren: Tagesumsatz mindestens 200 Kontrakte UND Prämie mindestens 100.000 $ (Umsatz x letzter Preis x 100).
Seite des Geschäfts (geschätzt!): liegt der letzte Preis im oberen Drittel zwischen Geld- und Briefkurs, gilt der Kontrakt als gekauft, im unteren Drittel als verkauft,
dazwischen bleibt er ungezählt. Das ist eine Näherung (nur der letzte Preis eines Tages, nicht jedes einzelne Geschäft) und kein echter Käufer-/Verkäufer-Flow.
Bullisch = gekaufte Calls + verkaufte Puts, bärisch = gekaufte Puts, Score = bullisch minus bärisch (verkaufte Calls zählen nicht, wie in der Vorlage).
Pro Tag und Aktie wird [gekaufte Calls, verkaufte Puts, gekaufte Puts, Prämie der gezählten Kontrakte in 1.000 $] gespeichert, 30 Handelstage (Tagesdaten sollen nicht anwachsen).
Zusätzlich je Aktie die 3 größten Kontrakte des neuesten Tages (Schlüssel gross, wird täglich ersetzt).
Ohne mindestens 250 abgerufene Aktien wird nichts überschrieben.
"""
import csv, datetime, io, json, os, re, sys, time, urllib.request
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0, os.path.dirname(__file__))
import optionsfluesse as of

ROOT = os.path.join(os.path.dirname(__file__), '..')
PFAD = os.path.join(ROOT, 'data', 'sektorflow.json')
LISTE = 'https://raw.githubusercontent.com/datasets/s-and-p-500-companies/main/data/constituents.csv'
ETFS = ['SPY', 'QQQ', 'IWM', 'DIA', 'TLT', 'GLD', 'SLV', 'HYG', 'EEM', 'SMH', 'XBI', 'XLK', 'XLV', 'XLI', 'XLY', 'XLF', 'XLC', 'XLB', 'XLE', 'XLP', 'XLU', 'XLRE']
MIN_VOL, MIN_PRAEMIE, MAX_TAGE, MIN_AKTIEN = 200, 100000, 30, 250

def firmen():
    req = urllib.request.Request(LISTE, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, timeout=60) as r:
        rows = csv.DictReader(io.StringIO(r.read().decode('utf-8')))
        return {x['Symbol'].replace('.', '-'): x['GICS Sector'] for x in rows}

def seite(bid, ask, last):
    """'K' gekauft, 'V' verkauft, None unklar: Lage des letzten Preises zwischen Geld und Brief."""
    if not ask or ask <= bid or not last: return None
    p = (last - bid) / (ask - bid)
    return 'K' if p >= 2 / 3 else 'V' if p <= 1 / 3 else None

def auswerten(j, sym):
    """Liefert (Datum, [gekaufte Calls, verkaufte Puts, gekaufte Puts, Prämie in 1.000 $], die 3 größten Kontrakte) aus einer Cboe-Kette.
    Kontrakt = [C|P, Strike, Verfall, Kontrakte, Prämie in 1.000 $, K|V|'' (geschätzte Seite)]; auch Kontrakte mit unklarer Seite stehen drin."""
    d = j.get('data', {}); cb = ps = pb = 0; pr = 0.0; gross = []
    for o in d.get('options') or []:
        m = re.fullmatch(r'([A-Z]+)(\d{6})([CP])(\d{8})', o.get('option', ''))
        if not m or m.group(1) != sym.replace('-', ''): continue
        vol = o.get('volume') or 0; last = o.get('last_trade_price') or 0
        if vol < MIN_VOL or vol * last * 100 < MIN_PRAEMIE: continue
        s = seite(o.get('bid') or 0, o.get('ask') or 0, last)
        e = m.group(2); gross.append([m.group(3), int(m.group(4)) / 1000, '20%s-%s-%s' % (e[:2], e[2:4], e[4:]), int(vol), int(round(vol * last * 100 / 1000)), s or ''])
        if (m.group(3), s) == ('C', 'K'): cb += 1
        elif (m.group(3), s) == ('P', 'V'): ps += 1
        elif (m.group(3), s) == ('P', 'K'): pb += 1
        else: continue
        pr += vol * last * 100
    gross.sort(key=lambda g: -g[4])
    return (j.get('timestamp') or '')[:10], [cb, ps, pb, int(round(pr / 1000))], gross[:3]

def holen(sym):
    for versuch in range(3):
        try:
            return of.holen(sym.replace('-', '.'))
        except Exception:
            time.sleep(2 + versuch * 3)
    return None

def eins(sym):
    j = holen(sym)
    if not j: return sym, None
    try: return sym, auswerten(j, sym)
    except Exception: return sym, None

def main():
    sektoren = firmen()
    for e in ETFS: sektoren.setdefault(e, 'ETF / Index')
    with ThreadPoolExecutor(4) as ex: erg = list(ex.map(eins, list(sektoren)))
    ok = [(s, r) for s, r in erg if r and r[0]]
    print('Abgerufen: %d von %d' % (len(ok), len(sektoren)))
    if len([1 for s, r in ok if sektoren[s] != 'ETF / Index']) < MIN_AKTIEN:
        sys.exit('zu wenig Aktien abgerufen, nichts geschrieben')
    tag = max(r[0] for s, r in ok)
    try: alt = json.load(open(PFAD, encoding='utf-8'))
    except Exception: alt = {'tage': {}}
    tage = alt.get('tage', {})
    tage[tag] = {s: r[1] for s, r in ok if r[0] == tag and any(r[1][:3])}
    gross = {s: r[2] for s, r in ok if r[0] == tag and r[2] and s in tage[tag]}   # nur der neueste Tag, damit nichts anwächst
    tage = {k: tage[k] for k in sorted(tage)[-MAX_TAGE:]}
    gebraucht = {s for t in tage.values() for s in t}
    out = {'stand': tag, 'schwellen': {'volumen': MIN_VOL, 'praemie_usd': MIN_PRAEMIE}, 'sektor': {s: sektoren[s] for s in sorted(gebraucht) if s in sektoren}, 'gross': gross, 'tage': tage}
    with open(PFAD, 'w', encoding='utf-8') as fh:
        fh.write(json.dumps(out, ensure_ascii=False, separators=(',', ':')).replace('},"', '},\n"') + '\n')
    print('Tag %s: %d Aktien mit Treffern' % (tag, len(tage[tag])))

if __name__ == '__main__':
    main()
