#!/usr/bin/env python3
"""Einmaliger Rückblick-Test des WCJ-Scores (Thomas, 19.10.2026) -> data/backtest-wcj.json

Frage: Wie zuverlässig waren die Aussagen des WCJ-Scores (trend.score, 12 Regeln, Stufen Stark/Momentum/Beobachten/Schwach) in der Vergangenheit?
Verfahren: Für jeden Handelstag der letzten JAHRE Jahre wird der Score so berechnet, als kenne man nur die Kurse bis zu diesem Tag (die Indikatoren sind
kausal, es fließt nichts aus der Zukunft ein). Danach wird gemessen, was der Kurs in den folgenden 5, 20 und 60 Handelstagen tat, absolut und gegen den S&P 500 (SPY).
Auswertung je Stufe (Zahl der Tage, mittlere Rendite, Trefferquote, Überrendite), Vergleich mit allen Tagen (Grundrate), Zusammenhang Punkte/Rendite
und je Regel (Regel erfüllt gegen nicht erfüllt). Wichtig: Benachbarte Tage überlappen, die Zahl unabhängiger Beobachtungen ist etwa Tage/20 (Horizont 20).
Aufruf: python3 tools/backtest-wcj.py [TICKER ...]   (Standard: AMZN + Vergleichswerte aus beobachtung.json/top10.json; Hauptwert = erster)
Nicht enthalten: Kosten, Steuern, Überlebensverzerrung (heutige Aktien), keine Handelsregel, nur Rückblick.
"""
import datetime, json, math, os, statistics, sys, time
sys.path.insert(0, os.path.dirname(__file__))
import trend

ROOT = os.path.join(os.path.dirname(__file__), '..')
PFAD = os.path.join(ROOT, 'data', 'backtest-wcj.json')
JAHRE = 3
HORIZONTE = (5, 20, 60)
STUFEN = ('Stark', 'Momentum im Aufbau', 'Beobachten', 'Schwach')

def datum(t): return datetime.datetime.utcfromtimestamp(t).strftime('%Y-%m-%d')

def tageswerte(zeilen, bench_dict, jahre=JAHRE):
    """Je Handelstag: Datum, Kurs, Score, Folgerenditen. zeilen = (t,o,h,l,c,v)."""
    c = [z[4] for z in zeilen]; n = len(c)
    m8, m21, m50, m200 = trend.ema_reihe(c, 8), trend.ema_reihe(c, 21), trend.sma_reihe(c, 50), trend.sma_reihe(c, 200)
    rsi = trend.rsi_reihe(c); ml, ms = trend.macd_reihen(c)
    ds = [datum(z[0]) for z in zeilen]
    bench, last = [], None
    for d in ds:                       # Vergleichsindex auf die Tage der Aktie ausrichten (letzten bekannten Stand fortschreiben)
        last = bench_dict.get(d, last); bench.append(last)
    start = max(210, n - 252 * jahre - max(HORIZONTE))
    rows = []
    for i in range(start, n):
        if None in (m200[i], m50[i]) or bench[i] is None: continue
        b = [x for x in bench[:i + 1] if x is not None]
        sc = trend.score(zeilen[:i + 1], c[:i + 1], m8[i], m21[i], m50[i], m200[i], rsi[i], ml[i], ms[i], b)
        r = {'d': ds[i], 'c': round(c[i], 2), 'p': sc['punkte'], 's': sc['stufe'], 'k': [1 if k['ok'] else 0 for k in sc['kriterien']]}
        for h in HORIZONTE:
            if i + h < n and bench[i + h] is not None and bench[i] is not None:
                a = c[i + h] / c[i] - 1; bm = bench[i + h] / bench[i] - 1
                r['f%d' % h] = a * 100; r['x%d' % h] = (a - bm) * 100
        rows.append(r)
    return rows

def mittel(v): return round(statistics.mean(v), 2) if v else None

def kennzahlen(rows):
    """Auswertung über beliebig viele Tageszeilen (auch mehrerer Aktien zusammen)."""
    out = {'tage': len(rows), 'stufen': {}, 'grundrate': {}, 'regeln': [], 'korrelation': {}}
    for h in HORIZONTE:
        f = [r['f%d' % h] for r in rows if 'f%d' % h in r]
        out['grundrate'][str(h)] = {'n': len(f), 'rendite': mittel(f), 'treffer': round(100 * sum(1 for x in f if x > 0) / len(f)) if f else None}
    for s in STUFEN:
        sub = [r for r in rows if r['s'] == s]
        e = {'tage': len(sub)}
        for h in HORIZONTE:
            f = [r['f%d' % h] for r in sub if 'f%d' % h in r]; x = [r['x%d' % h] for r in sub if 'x%d' % h in r]
            e[str(h)] = {'n': len(f), 'rendite': mittel(f), 'ueber': mittel(x), 'treffer': round(100 * sum(1 for v in f if v > 0) / len(f)) if f else None}
        out['stufen'][s] = e
    for h in (20,):
        p = [(r['p'], r['f%d' % h]) for r in rows if 'f%d' % h in r]
        if len(p) > 20:
            xs, ys = [a for a, _ in p], [b for _, b in p]
            sx, sy = statistics.pstdev(xs), statistics.pstdev(ys)
            rr = sum((a - statistics.mean(xs)) * (b - statistics.mean(ys)) for a, b in p) / len(p) / (sx * sy) if sx and sy else None
            neff = len(p) / h
            out['korrelation'] = {'r': None if rr is None else round(rr, 3), 'n': len(p), 'n_eff': round(neff), 'schwelle': round(2 / math.sqrt(neff), 2)}
    namen = None
    for k in range(12):
        ja = [r['f20'] for r in rows if 'f20' in r and r['k'][k]]; nein = [r['f20'] for r in rows if 'f20' in r and not r['k'][k]]
        out['regeln'].append({'nr': k + 1, 'ja_tage': len(ja), 'ja': mittel(ja), 'nein': mittel(nein), 'diff': None if not ja or not nein else round(statistics.mean(ja) - statistics.mean(nein), 2)})
    return out

def vergleichswerte():
    out = []
    for datei, key in (('beobachtung.json', 'aktien'), ('top10.json', 'top10')):
        try:
            for x in json.load(open(os.path.join(ROOT, 'data', datei), encoding='utf-8')).get(key, []):
                if x.get('ticker') and x['ticker'] not in out: out.append(x['ticker'])
        except Exception as e: print('Liste', datei, e)
    return out

def main():
    args = [a.upper() for a in sys.argv[1:]]
    haupt = args[0] if args else 'AMZN'
    liste = args if len(args) > 1 else [haupt] + [t for t in vergleichswerte() if t != haupt]
    meta, spy = trend.holen('SPY', '6y')
    bd = {datum(z[0]): z[4] for z in spy}
    alle, je, haupt_rows = [], {}, None
    for t in liste:
        try:
            _, z = trend.holen(t, '6y'); time.sleep(0.5)
            rows = tageswerte(z, bd)
        except Exception as e:
            print(t, 'Fehler:', e); continue
        je[t] = kennzahlen(rows); alle += rows
        print(t, len(rows), 'Tage', {s: je[t]['stufen'][s]['tage'] for s in STUFEN})
        if t == haupt: haupt_rows = rows
    if not haupt_rows: print('Hauptwert nicht abrufbar'); sys.exit(1)
    letztes = [r for r in haupt_rows if r['d'] >= (datetime.date.today() - datetime.timedelta(days=365)).isoformat()]
    wochen = letztes[::5]
    out = {'stand': datetime.date.today().isoformat(), 'hauptwert': haupt, 'jahre': JAHRE, 'horizonte': HORIZONTE,
           'hinweis': 'Rückblick, keine Prognose. Überlappende Zeiträume; unabhängige Beobachtungen etwa Tage/20. Ohne Kosten und ohne Überlebensverzerrung.',
           'haupt': kennzahlen(haupt_rows), 'haupt_letztes_jahr': kennzahlen(letztes),
           'verlauf': [{'d': r['d'], 'c': r['c'], 'p': r['p'], 's': r['s'], 'f20': None if 'f20' not in r else round(r['f20'], 1), 'x20': None if 'x20' not in r else round(r['x20'], 1)} for r in wochen],
           'alle': kennzahlen(alle), 'je_aktie': {t: {'tage': v['tage'], 'korrelation': v['korrelation'], 'stark20': v['stufen']['Stark']['20'], 'schwach20': v['stufen']['Schwach']['20']} for t, v in je.items()}}
    json.dump(out, open(PFAD, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('geschrieben', PFAD)

if __name__ == '__main__':
    main()
