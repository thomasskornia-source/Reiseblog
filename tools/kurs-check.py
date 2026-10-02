#!/usr/bin/env python3
"""Kurs gegen gleitende Durchschnitte (für James im Aktien-Check), Logik in tools/trend.py.

Aufruf:  python3 tools/kurs-check.py KO                  gibt Kurs, Linien, Ampel (Up/Medium/Down) und Lage als JSON aus
         python3 tools/kurs-check.py KO --schreibe       schreibt zusätzlich die Zahlen und den 80-Tage-Verlauf (Chart)
                                                         in den vorhandenen Eintrag in data/aktien.json (Feld "james")
Ticker: US `KO`, Xetra `SIE.DE`, London `.L`, Paris `.PA`.
--schreibe setzt nur die Zahlenfelder (kurs, ma8, ma21, ma50, ma200, abstand_pct, ma200_steigt, waehrung, kurs_stand,
ampel, lage, serie) und lässt Texte und Urteile unberührt; gibt es noch keinen Eintrag mit diesem Symbol, passiert nichts.
Fehler: Exit-Code 1 und „FEHLER: …“ – dann keine Zahlen erfinden.
"""
import json, os, re, sys
sys.path.insert(0, os.path.dirname(__file__))
import trend

PFAD = os.path.join(os.path.dirname(__file__), '..', 'data', 'aktien.json')

def kompakt(text):
    """Zahlenlisten in einer Zeile halten, damit die Datei lesbar und klein bleibt."""
    return re.sub(r'\[\s*((?:-?[\d.]+(?:e[-+]?\d+)?,?\s*|"[^"]*",?\s*)+)\]',
                  lambda m: '[' + re.sub(r'\s*\n\s*', ' ', m.group(1)).strip() + ']', text)

def schreiben(sym, a):
    with open(PFAD, encoding='utf-8') as f:
        d = json.load(f)
    def symbol(e): return (e.get('symbol') or str(e.get('ticker', '')).split(' ')[0]).upper()
    ziel = [e for e in d['einschaetzungen'] if symbol(e) == sym.upper()]
    if not ziel:
        print('HINWEIS: kein Eintrag für %s in data/aktien.json, nichts geschrieben' % sym); return
    j = ziel[-1].setdefault('james', {})
    for k in ('kurs', 'ma8', 'ma21', 'ma50', 'ma200', 'abstand_pct', 'ma200_steigt', 'waehrung', 'ampel', 'lage', 'serie'):
        j[k] = a[k]
    j['kurs_stand'] = a['stand']
    ziel[-1].setdefault('symbol', sym.upper())
    with open(PFAD, 'w', encoding='utf-8') as f:
        f.write(kompakt(json.dumps(d, ensure_ascii=False, indent=2)) + '\n')
    print('OK: Zahlen und Chart in den Eintrag %s geschrieben' % sym.upper())

def main():
    args = [x for x in sys.argv[1:] if not x.startswith('--')]
    if len(args) != 1: sys.exit(__doc__)
    sym = args[0].strip().upper()
    try:
        meta, zeilen = trend.holen(sym)
        a = trend.analyse(zeilen, meta)
    except Exception as e:
        print('FEHLER: Kursdaten für %s nicht abrufbar oder zu kurz (%s)' % (sym, e)); sys.exit(1)
    kurz = {k: v for k, v in a.items() if k != 'serie'}
    kurz.update({'ticker': sym, 'quelle': 'Yahoo Finance (Tageskurse)'})
    print(json.dumps(kurz, ensure_ascii=False, indent=2))
    if '--schreibe' in sys.argv: schreiben(sym, a)

main()
