#!/usr/bin/env python3
"""Sucht in den Berkshire-Aktionärsbriefen (wissen/briefe/<jahr>.txt).

Aufruf:  python3 wissen/suche.py Begriff [Begriff ...] [--max 8] [--jahre 1990-2005]
Gibt Absätze aus, die ALLE Begriffe enthalten (ohne Groß-/Kleinschreibung), neueste zuerst,
jeweils mit Jahr und Absatznummer. Die Texte sind Englisch (Originalsprache der Briefe).
"""
import re, sys, pathlib

def main():
    args = sys.argv[1:]
    mx, von, bis, terms = 8, 0, 9999, []
    i = 0
    while i < len(args):
        if args[i] == '--max': mx = int(args[i + 1]); i += 2
        elif args[i] == '--jahre':
            a, _, b = args[i + 1].partition('-'); von, bis = int(a), int(b or a); i += 2
        else: terms.append(args[i].lower()); i += 1
    if not terms:
        sys.exit(__doc__)
    ordner = pathlib.Path(__file__).parent / 'briefe'
    treffer = []
    for f in sorted(ordner.glob('*.txt'), reverse=True):
        jahr = int(f.stem)
        if not von <= jahr <= bis: continue
        for n, p in enumerate(re.split(r'\n\s*\n', f.read_text(encoding='utf-8')), 1):
            q = ' '.join(p.split())
            if len(q) > 80 and all(t in q.lower() for t in terms):
                treffer.append((jahr, n, q))
    for jahr, n, q in treffer[:mx]:
        print(f'[{jahr} ¶{n}] {q[:900]}{"…" if len(q) > 900 else ""}\n')
    print(f'{len(treffer)} Treffer, {min(mx, len(treffer))} gezeigt.', file=sys.stderr)

main()
