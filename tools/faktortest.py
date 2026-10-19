#!/usr/bin/env python3
"""Faktor-Rückblick (Thomas, 19.10.2026) -> data/faktortest.json

Frage: Welche der 12 WCJ-Regeln (und welche zusätzlichen Kandidaten) hatten in der Vergangenheit Vorhersagekraft für spätere Aktienrenditen?
Verfahren (übliches Querschnitt-Verfahren): Am letzten Handelstag jedes Monats wird jeder Faktor für alle S&P-500-Aktien so berechnet, als kenne man nur die Kurse bis dahin.
Dann Vergleich mit der Rendite der folgenden 1, 3, 6 und 12 Monate:
  ic       Rangkorrelation (Faktor gegen spätere Rendite) je Monat, gemittelt (0 = kein Zusammenhang)
  spread   mittlere Rendite der obersten 20 % minus der untersten 20 % (bei Ja/Nein-Regeln: erfüllt minus nicht erfüllt), Prozentpunkte
  t        mittlere IC geteilt durch ihren Standardfehler; überlappende Zeiträume werden berücksichtigt (n_eff = Monate / Horizont)
Zeiträume: gesamt sowie erste und zweite Hälfte getrennt (Entwicklung gegen Gegenprobe). Urteil je Horizont:
  traegt   |t| >= 2,5 gesamt, gleiches Vorzeichen in beiden Hälften, je Hälfte |t| >= 1
  dreht    beide Hälften je |t| >= 1, aber mit entgegengesetztem Vorzeichen
  nicht    |t| < 1,5 gesamt
  unklar   alles dazwischen
Bei rund 30 Faktoren x 4 Horizonten sind einzelne Zufallstreffer zu erwarten; ein Urteil gilt erst mit Blick auf beide Hälften.
Grenzen: heutige Index-Mitglieder (Überlebensverzerrung), Yahoo-Kurse (inoffiziell), keine Kosten/Steuern, Rückblick ist keine Prognose.
Aufruf: python3 tools/faktortest.py [Anzahl_Aktien]   (ohne Zahl: alle)
"""
import csv, datetime, io, json, math, os, sys, time, urllib.request
from concurrent.futures import ThreadPoolExecutor
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
import trend

ROOT = os.path.join(os.path.dirname(__file__), '..')
PFAD = os.path.join(ROOT, 'data', 'faktortest.json')
LISTE = 'https://raw.githubusercontent.com/datasets/s-and-p-500-companies/main/data/constituents.csv'
HOR = {'1': 21, '3': 63, '6': 126, '12': 252}      # Handelstage je Monatshorizont
HM = {'1': 1, '3': 3, '6': 6, '12': 12}
TEILUNG = '2022-01'                                 # erste Hälfte vor, zweite ab diesem Monat

# Kandidaten: Schlüssel -> (Name, Beschreibung)
KAND = {
    'mom12_1': ('Momentum 12 Monate ohne letzten Monat', 'Rendite von vor 12 bis vor 1 Monat (Standard-Momentum der Forschung)'),
    'mom6_1': ('Momentum 6 Monate ohne letzten Monat', 'Rendite von vor 6 bis vor 1 Monat'),
    'mom3': ('Rendite 3 Monate', 'Kurs gegen Kurs vor 63 Handelstagen'),
    'ret1m': ('Rendite letzter Monat', 'Kurzfristige Rendite (Umkehr-Effekt?)'),
    'ret1w': ('Rendite letzte Woche', 'Rendite der letzten 5 Handelstage'),
    'vol60': ('Schwankungsstärke 60 Tage', 'Standardabweichung der Tagesrenditen (hoch = unruhig)'),
    'atrpct': ('ATR in Prozent des Kurses', 'Durchschnittliche Tagesspanne (14 Tage) im Verhältnis zum Kurs'),
    'rsi2': ('RSI mit 2 Tagen', 'Sehr kurzfristiger Überkauft/Überverkauft-Wert'),
    'rsi14': ('RSI mit 14 Tagen', 'Üblicher RSI'),
    'dist_hoch': ('Abstand zum 52-Wochen-Hoch', 'Kurs gegen Hoch der letzten 252 Tage (0 = am Hoch)'),
    'dist_tief': ('Abstand zum 52-Wochen-Tief', 'Kurs gegen Tief der letzten 252 Tage'),
    'dist_ma50': ('Abstand zur 50-Tage-Linie', 'Kurs gegen den 50-Tage-Durchschnitt'),
    'dist_ma200': ('Abstand zur 200-Tage-Linie', 'Kurs gegen den 200-Tage-Durchschnitt'),
    'steig200': ('Steigung der 200-Tage-Linie', '200er heute gegen vor 21 Tagen'),
    'volspike': ('Umsatz-Spitze', 'Umsatz der letzten 5 Tage gegen 50-Tage-Schnitt'),
    'punkte': ('WCJ-Score (Punkte)', 'Gesamtpunkte 0 bis 11 nach den aktuellen Gewichten'),
}
REGELN = ['MA FAN (Kurs über 8, 21, 50 geordnet)', 'Über steigender 200er (Pflicht)', 'Über 10-Wochen-EMA', 'Höhere Hochs und Tiefs',
          'Höchstens 5 % unter 52-Wochen-Hoch', 'Besser als S&P 500 (3 Monate)', 'RSI zwischen 50 und 75', 'MACD über Signallinie',
          'Mehr Umsatz an Auf- als an Abtagen', 'OBV steigt', 'Squeeze / enge ATR', 'NR7 oder Umsatz trocknet aus']

def web(url, ua='Mozilla/5.0'):
    req = urllib.request.Request(url, headers={'User-Agent': ua})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read()

def tickerliste():
    rows = csv.DictReader(io.StringIO(web(LISTE).decode('utf-8')))
    return [r['Symbol'].replace('.', '-') for r in rows]

def datum(t): return datetime.datetime.utcfromtimestamp(t).strftime('%Y-%m-%d')

def monatsende(daten):
    """Indizes der letzten Handelstage je Monat in einer sortierten Datumsliste."""
    out = []
    for i in range(len(daten) - 1):
        if daten[i][:7] != daten[i + 1][:7]: out.append(i)
    return out

def faktoren(zeilen, bench_dict, tage):
    """Je Monatsende-Datum (aus tage): Faktorwerte, Regel-Flags und Folgerenditen. Alles nur mit Daten bis zu dem Tag."""
    c = np.array([z[4] for z in zeilen], float); h = np.array([z[2] for z in zeilen], float)
    l = np.array([z[3] for z in zeilen], float); v = np.array([z[5] for z in zeilen], float)
    cl = list(c); ds = [datum(z[0]) for z in zeilen]; n = len(c)
    m8, m21, m50, m200 = trend.ema_reihe(cl, 8), trend.ema_reihe(cl, 21), trend.sma_reihe(cl, 50), trend.sma_reihe(cl, 200)
    rsi14 = trend.rsi_reihe(cl); rsi2 = trend.rsi_reihe(cl, 2); ml, ms = trend.macd_reihen(cl)
    bench, last = [], None
    for d in ds:
        last = bench_dict.get(d, last); bench.append(last)
    lr = np.diff(np.log(c), prepend=np.nan)
    tr = np.maximum.reduce([h[1:] - l[1:], np.abs(h[1:] - c[:-1]), np.abs(l[1:] - c[:-1])])
    pos = {d: i for i, d in enumerate(ds)}
    out = {}
    for d in tage:
        i = pos.get(d)
        if i is None or i < 253 or m200[i] is None or bench[i] is None: continue
        b = [x for x in bench[:i + 1] if x is not None]
        try:
            sc = trend.score(zeilen[:i + 1], cl[:i + 1], m8[i], m21[i], m50[i], m200[i], rsi14[i], ml[i], ms[i], b)
        except Exception:
            continue
        f = {
            'mom12_1': c[i - 21] / c[i - 252] - 1, 'mom6_1': c[i - 21] / c[i - 126] - 1, 'mom3': c[i] / c[i - 63] - 1, 'ret1m': c[i] / c[i - 21] - 1,
            'ret1w': c[i] / c[i - 5] - 1, 'vol60': float(np.nanstd(lr[i - 59:i + 1])), 'atrpct': float(np.mean(tr[i - 14:i]) / c[i]),
            'rsi2': rsi2[i], 'rsi14': rsi14[i], 'dist_hoch': c[i] / h[i - 251:i + 1].max() - 1, 'dist_tief': c[i] / l[i - 251:i + 1].min() - 1,
            'dist_ma50': c[i] / m50[i] - 1, 'dist_ma200': c[i] / m200[i] - 1, 'steig200': m200[i] / m200[i - 21] - 1,
            'volspike': float(v[i - 4:i + 1].mean() / max(v[i - 49:i + 1].mean(), 1)), 'punkte': float(sc['punkte']),
        }
        for k, x in enumerate(sc['kriterien']): f['r%d' % (k + 1)] = 1.0 if x['ok'] else 0.0
        for hk, hd in HOR.items():
            f['f' + hk] = (c[i + hd] / c[i] - 1) * 100 if i + hd < n else None
        out[d] = f
    return out

def rang(a):
    u, inv, cnt = np.unique(a, return_inverse=True, return_counts=True)
    cs = np.cumsum(cnt)
    return (cs - (cnt - 1) / 2)[inv]

def querschnitt(x, y):
    """(IC, Spread) für einen Monat. x Faktor, y spätere Rendite (Prozent)."""
    ok = ~(np.isnan(x) | np.isnan(y)); x, y = x[ok], y[ok]
    if len(x) < 50 or np.ptp(x) == 0: return None
    rx, ry = rang(x), rang(y)
    ic = float(np.corrcoef(rx, ry)[0, 1])
    if len(np.unique(x)) <= 2:
        hi = y[x == x.max()]; lo = y[x == x.min()]
    else:
        p = (rx - 0.5) / len(rx); hi = y[p >= 0.8]; lo = y[p <= 0.2]
    if len(hi) < 5 or len(lo) < 5: return None
    return ic, float(hi.mean() - lo.mean())

def tstat(reihe, hm):
    r = np.array(reihe, float)
    if len(r) < 6: return None
    neff = len(r) / hm
    if neff < 3 or r.std(ddof=1) == 0: return None
    return float(r.mean() / (r.std(ddof=1) / math.sqrt(neff)))

def urteil(t, t1, t2, m1, m2):
    if t is None or t1 is None or t2 is None: return 'unklar'
    if abs(t) < 1.5: return 'nicht'
    if np.sign(m1) == np.sign(m2) == np.sign(t) and abs(t) >= 2.5 and abs(t1) >= 1 and abs(t2) >= 1: return 'traegt'
    if np.sign(m1) != np.sign(m2) and abs(t1) >= 1 and abs(t2) >= 1: return 'dreht'
    return 'unklar'

def auswerten(zeit):
    """zeit: {datum: {aktie: faktor-dict}} -> Kennzahlen je Faktor und Horizont."""
    monate = sorted(zeit)
    namen = list(KAND) + ['r%d' % k for k in range(1, 13)]
    res = {}
    for nm in namen:
        res[nm] = {}
        for hk, hm in HM.items():
            ics, sps, mon = [], [], []
            for d in monate:
                a = zeit[d]
                x = np.array([a[t][nm] if nm in a[t] and a[t][nm] is not None else np.nan for t in a], float)
                y = np.array([a[t]['f' + hk] if a[t].get('f' + hk) is not None else np.nan for t in a], float)
                q = querschnitt(x, y)
                if q: ics.append(q[0]); sps.append(q[1]); mon.append(d[:7])
            if len(ics) < 12: res[nm][hk] = None; continue
            e1 = [i for i, m in enumerate(mon) if m < TEILUNG]; e2 = [i for i, m in enumerate(mon) if m >= TEILUNG]
            pick = lambda s, ix: [s[i] for i in ix]
            t = tstat(ics, hm); t1 = tstat(pick(ics, e1), hm); t2 = tstat(pick(ics, e2), hm)
            m1 = float(np.mean(pick(ics, e1))) if e1 else 0.0; m2 = float(np.mean(pick(ics, e2))) if e2 else 0.0
            r = lambda v, k=3: None if v is None else round(v, k)
            res[nm][hk] = {'monate': len(ics), 'ic': r(float(np.mean(ics))), 'ic1': r(m1), 'ic2': r(m2), 't': r(t, 2), 't1': r(t1, 2), 't2': r(t2, 2),
                           'spread': r(float(np.mean(sps)), 2), 'spread1': r(float(np.mean(pick(sps, e1))) if e1 else None, 2),
                           'spread2': r(float(np.mean(pick(sps, e2))) if e2 else None, 2), 'urteil': urteil(t, t1, t2, m1, m2)}
    return res

def gesamturteil(r):
    u = {hk: (r.get(hk) or {}).get('urteil') for hk in HM}
    if any(x == 'traegt' for x in u.values()): return 'traegt'
    if any(x == 'dreht' for x in u.values()): return 'dreht'
    if all(x == 'nicht' for x in u.values() if x): return 'nicht'
    return 'unklar'

def korrelation(zeit):
    zeilen = []
    for d in zeit:
        for t, f in zeit[d].items(): zeilen.append([f['r%d' % k] for k in range(1, 13)])
    if len(zeilen) < 100: return None
    m = np.corrcoef(np.array(zeilen, float).T)
    return [[round(float(x), 2) if not np.isnan(x) else 0 for x in row] for row in m]

def main():
    liste = tickerliste()
    if len(sys.argv) > 1: liste = liste[:int(sys.argv[1])]
    print('Aktien in der Liste:', len(liste))
    _, spy = trend.holen('SPY', '10y')
    bd = {datum(z[0]): z[4] for z in spy}
    tage = [datum(spy[i][0]) for i in monatsende([datum(z[0]) for z in spy]) if i >= 253]
    print('Monatsenden:', len(tage), tage[0], '…', tage[-1])
    def hole(t):
        err = None
        for v in range(3):
            try:
                return t, trend.holen(t, '10y')[1]
            except Exception as e:
                time.sleep(2 * (v + 1)); err = e
        print(t, 'Fehler:', err); return t, None
    zeit, ok = {}, 0
    with ThreadPoolExecutor(6) as ex:
        for t, z in ex.map(hole, liste):
            if not z or len(z) < 400: continue
            try:
                f = faktoren(z, bd, tage)
            except Exception as e:
                print(t, 'Rechenfehler:', e); continue
            for d, v in f.items(): zeit.setdefault(d, {})[t] = v
            ok += 1
            if ok % 50 == 0: print(ok, 'Aktien gerechnet')
    if ok < len(liste) * 0.6: print('Zu wenige Aktien (%d), nichts geschrieben' % ok); sys.exit(1)
    res = auswerten(zeit)
    faktoren_out = []
    for k, (name, besch) in KAND.items(): faktoren_out.append({'id': k, 'name': name, 'beschreibung': besch, 'art': 'kandidat', 'horizonte': res[k], 'urteil': gesamturteil(res[k])})
    for k in range(1, 13):
        nm = 'r%d' % k
        faktoren_out.append({'id': nm, 'name': REGELN[k - 1], 'beschreibung': 'WCJ-Regel %d (ja/nein)' % k, 'art': 'regel', 'horizonte': res[nm], 'urteil': gesamturteil(res[nm])})
    out = {'stand': datetime.date.today().isoformat(), 'aktien': ok, 'monate': len(zeit), 'von': tage[0], 'bis': tage[-1], 'teilung': TEILUNG,
           'hinweis': 'Rückblick, keine Prognose. Heutige Index-Mitglieder (Überlebensverzerrung), keine Kosten. Bei vielen Tests sind einzelne Zufallstreffer zu erwarten.',
           'faktoren': faktoren_out, 'regelkorrelation': korrelation(zeit), 'regelnamen': REGELN}
    json.dump(out, open(PFAD, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('geschrieben', PFAD, {u: sum(1 for f in faktoren_out if f['urteil'] == u) for u in ('traegt', 'dreht', 'unklar', 'nicht')})

if __name__ == '__main__':
    main()
