#!/usr/bin/env python3
"""Sammelt täglich den Option-Flows-Tageswert aller US-Aktien aus data/aktien.json (Verlauf für die Jahresbewertung).

Aufruf:  python3 tools/flows-sammeln.py     läuft täglich nach US-Börsenschluss per GitHub-Aktion (flows.yml)
Schreibt data/flows/<Ticker>.json (ein Wert je Handelstag, höchstens 252). Aktien ohne US-Optionen werden übersprungen.
"""
import json, os, sys, time
sys.path.insert(0, os.path.dirname(__file__))
import optionsfluesse as of

def main():
    with open(of.AKTIEN, encoding='utf-8') as f:
        d = json.load(f)
    symbole = []
    for e in d['einschaetzungen']:
        s = (e.get('symbol') or str(e.get('ticker', '')).split(' ')[0]).upper()
        if s and s not in symbole: symbole.append(s)
    ok = 0
    for s in symbole:
        try:
            o = of.auswerten(s)
        except of.Fehler as e:
            print('übersprungen %s: %s' % (s, e)); continue
        of.verlauf_speichern(o['symbol'], o); ok += 1
        print('%s: %s, relativ %s, Tage %d' % (o['symbol'], o['richtung'], o['put_call_relativ'], len(of.verlauf_lesen(o['symbol']))))
        time.sleep(1)
    print('%d von %d Aktien gespeichert' % (ok, len(symbole)))

main()
