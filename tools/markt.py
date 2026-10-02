#!/usr/bin/env python3
"""Marktstimmung S&P 500 (Indikator Up / Medium / Down) nach der Trend-Logik in tools/trend.py.

Aufruf:  python3 tools/markt.py            schreibt data/markt.json (läuft täglich per GitHub-Aktion)
Fehler:  Exit-Code 1 und „FEHLER: …“, die Datei bleibt dann unverändert.
"""
import json, os, sys
sys.path.insert(0, os.path.dirname(__file__))
import trend

def main():
    try:
        meta, zeilen = trend.holen('^GSPC')
        a = trend.analyse(zeilen, meta)
    except Exception as e:
        print('FEHLER: S&P 500 nicht abrufbar (%s)' % e); sys.exit(1)
    a.pop('serie')
    a.update({'name': 'S&P 500', 'quelle': 'Yahoo Finance (Tageskurse)'})
    pfad = os.path.join(os.path.dirname(__file__), '..', 'data', 'markt.json')
    with open(pfad, 'w', encoding='utf-8') as f:
        json.dump(a, f, ensure_ascii=False, indent=2); f.write('\n')
    print(json.dumps(a, ensure_ascii=False))

main()
