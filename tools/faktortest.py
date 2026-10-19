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
Zusätze (20.10.2026): (1) zweite Auswertung mit Rendite minus Beta mal Marktrendite (adj), Beta nur aus den 252 Tagen davor; (2) Kennzahlen aus den SEC-Jahresabschlüssen
(companyfacts, nur Werte, die am Stichtag schon gemeldet waren): Eigenkapitalrendite, Margen, Umsatzwachstum, Gewinn- und Free-Cashflow-Rendite, Verschuldung, Accruals.
Aufruf: python3 tools/faktortest.py [Anzahl_Aktien]   (ohne Zahl: alle)
"""
import csv, datetime, io, json, math, os, sys, threading, time, urllib.request
from concurrent.futures import ThreadPoolExecutor
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
import trend

ROOT = os.path.join(os.path.dirname(__file__), '..')
UNI = os.environ.get('UNIVERSUM', 'sp500').strip().lower()      # sp500 | sp400 | sp600 | europa
UNI_NAMEN = {'sp500': 'S&P 500 (große US-Werte)', 'sp400': 'S&P MidCap 400 (mittlere US-Werte)', 'sp600': 'S&P SmallCap 600 (kleine US-Werte)',
             'europa': 'Europa (rund 90 große Werte, Yahoo-Kürzel)'}
BENCH = {'sp500': 'SPY', 'sp400': 'MDY', 'sp600': 'IJR', 'europa': '^STOXX50E'}
PFAD = os.path.join(ROOT, 'data', 'faktortest.json' if UNI == 'sp500' else 'faktortest-%s.json' % UNI)
WIKI = {'sp400': 'https://en.wikipedia.org/wiki/List_of_S%26P_400_companies', 'sp600': 'https://en.wikipedia.org/wiki/List_of_S%26P_600_companies'}
EUROPA = ('ASML.AS ADYEN.AS INGA.AS PHIA.AS HEIA.AS AD.AS WKL.AS PRX.AS SAP.DE SIE.DE ALV.DE DTE.DE MUV2.DE BAS.DE BAYN.DE BMW.DE MBG.DE VOW3.DE '
          'DBK.DE ADS.DE IFX.DE DHL.DE RWE.DE EOAN.DE HEN3.DE FRE.DE MRK.DE SY1.DE BEI.DE CON.DE HNR1.DE MC.PA OR.PA TTE.PA SAN.PA AIR.PA SU.PA AI.PA '
          'BNP.PA CS.PA RMS.PA KER.PA DG.PA SGO.PA BN.PA CAP.PA VIV.PA ORA.PA EL.PA STLAM.MI ENEL.MI ENI.MI ISP.MI UCG.MI RACE.MI G.MI SAN.MC IBE.MC '
          'ITX.MC BBVA.MC TEF.MC REP.MC NESN.SW ROG.SW NOVN.SW ZURN.SW UBSG.SW ABBN.SW CFR.SW SREN.SW HOLN.SW ALC.SW SHEL.L AZN.L ULVR.L HSBA.L BP.L '
          'GSK.L DGE.L RIO.L BATS.L LSEG.L REL.L NG.L VOD.L BARC.L LLOY.L NOVO-B.CO CARL-B.CO VWS.CO VOLV-B.ST ERIC-B.ST ATCO-A.ST EQNR.OL NOKIA.HE').split()
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
    'beta': ('Beta (252 Tage)', 'Empfindlichkeit gegenüber dem S&P 500 (Tagesrenditen der letzten 252 Tage)'),
    'roe': ('Eigenkapitalrendite', 'Jahresgewinn / Eigenkapital (letzter Jahresabschluss, nur wenn schon veröffentlicht)'),
    'opm': ('Operative Marge', 'Operatives Ergebnis / Umsatz (Jahresabschluss)'),
    'gpm': ('Bruttomarge', 'Bruttogewinn / Umsatz (Jahresabschluss)'),
    'wachstum': ('Umsatzwachstum', 'Umsatz gegen Vorjahr (Jahresabschluss)'),
    'ep': ('Gewinnrendite (E/P)', 'Jahresgewinn / Börsenwert (Kurs am Tag, Aktienzahl aus dem Abschluss)'),
    'fcfy': ('Free-Cashflow-Rendite', '(Cashflow aus Betrieb minus Investitionen) / Börsenwert'),
    'schulden': ('Verschuldung', 'Verbindlichkeiten / Bilanzsumme'),
    'accruals': ('Accruals (Gewinnqualität)', '(Gewinn minus operativer Cashflow) / Bilanzsumme; niedrig = Gewinn durch Cash gedeckt'),
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
    if UNI == 'europa': return [(t, None) for t in EUROPA]
    if UNI in WIKI: return wiki_liste()
    rows = csv.DictReader(io.StringIO(web(LISTE).decode('utf-8')))
    return [(r['Symbol'].replace('.', '-'), int(r['CIK'])) for r in rows]

def wiki_liste():
    """S&P 400/600: Kürzel aus der ersten Tabelle der Wikipedia-Liste, CIK aus der SEC-Zuordnung company_tickers.json."""
    import re
    ua = 'Reiseblog Faktortest %s' % os.environ.get('SEC_KONTAKT', 'kontakt@example.com')
    html = web(WIKI[UNI], ua).decode('utf-8', 'replace')
    tab = html[html.find('<table class="wikitable'):]
    tab = tab[:tab.find('</table>')]
    syms = []
    for tr in re.findall(r'<tr>(.*?)</tr>', tab, re.S)[1:]:
        td = re.findall(r'<td[^>]*>(.*?)</td>', tr, re.S)
        if not td: continue
        t = re.sub(r'<[^>]+>', '', td[0]).strip().replace('.', '-')
        if re.fullmatch(r'[A-Z][A-Z0-9-]{0,5}', t): syms.append(t)
    try: cik = {v['ticker'].replace('.', '-'): int(v['cik_str']) for v in json.loads(web('https://www.sec.gov/files/company_tickers.json', ua)).values()}
    except Exception as e: print('CIK-Liste nicht geladen:', e); cik = {}
    print('Kürzel aus Wikipedia:', len(syms), 'mit CIK:', sum(1 for t in syms if t in cik))
    return [(t, cik.get(t)) for t in dict.fromkeys(syms)]

def datum(t): return datetime.datetime.utcfromtimestamp(t).strftime('%Y-%m-%d')

def monatsende(daten):
    """Indizes der letzten Handelstage je Monat in einer sortierten Datumsliste."""
    out = []
    for i in range(len(daten) - 1):
        if daten[i][:7] != daten[i + 1][:7]: out.append(i)
    return out

SEC = 'https://data.sec.gov/api/xbrl/companyfacts/CIK%010d.json'
TAGS = {
    'umsatz': ['Revenues', 'RevenueFromContractWithCustomerExcludingAssessedTax', 'SalesRevenueNet', 'RevenueFromContractWithCustomerIncludingAssessedTax'],
    'gewinn': ['NetIncomeLoss'], 'betrieb': ['OperatingIncomeLoss'], 'brutto': ['GrossProfit'],
    'eigenkapital': ['StockholdersEquity'], 'bilanz': ['Assets'], 'verbind': ['Liabilities'],
    'ocf': ['NetCashProvidedByUsedInOperatingActivities'], 'capex': ['PaymentsToAcquirePropertyPlantAndEquipment'],
}

def sec_kompakt(js):
    """Aus companyfacts nur Jahresabschlüsse (10-K): je Kennzahl Liste (Ende, Beginn oder None, Wert, Meldedatum). Plus Aktienzahl vom Deckblatt."""
    out = {}
    gaap = js.get('facts', {}).get('us-gaap', {})
    for key, tags in TAGS.items():
        rows = {}
        for tg in tags:
            for x in gaap.get(tg, {}).get('units', {}).get('USD', []):
                if x.get('form') not in ('10-K', '10-K/A') or x.get('fp') != 'FY': continue
                b, e = x.get('start'), x.get('end')
                if key in ('eigenkapital', 'bilanz', 'verbind'):
                    if b: continue
                else:
                    if not b: continue
                    try:
                        dd = (datetime.date.fromisoformat(e) - datetime.date.fromisoformat(b)).days
                    except Exception: continue
                    if not 350 <= dd <= 380: continue
                rows.setdefault((e, tg), []).append((e, b, x['val'], x['filed']))
        flat = {}
        for (e, tg), lst in rows.items():       # Reihenfolge der Tags = Vorrang; je Ende den frühesten Meldestand behalten
            lst.sort(key=lambda r: r[3])
            if e not in flat or tags.index(tg) < flat[e][0]: flat[e] = (tags.index(tg), lst[0])
        out[key] = sorted([v[1] for v in flat.values()])
    sh = []
    for x in js.get('facts', {}).get('dei', {}).get('EntityCommonStockSharesOutstanding', {}).get('units', {}).get('shares', []):
        if x.get('form') in ('10-K', '10-K/A'): sh.append((x['end'], None, x['val'], x['filed']))
    out['aktien'] = sorted(sh)
    return out

def stand(reihe, tag):
    """Jüngster am Tag schon gemeldeter Wert und der Wert des Vorjahres. (Ende, Wert, Meldedatum) oder None."""
    ok = [r for r in reihe if r[3] <= tag]
    if not ok: return None, None
    ok.sort(key=lambda r: (r[0], r[3]))
    last = ok[-1]
    if (datetime.date.fromisoformat(tag) - datetime.date.fromisoformat(last[3])).days > 450: return None, None
    prev = None
    for r in ok[:-1]:
        d = (datetime.date.fromisoformat(last[0]) - datetime.date.fromisoformat(r[0])).days
        if 330 <= d <= 400: prev = r
    return last, prev

def fundamental(f, tag, kurs):
    """Kennzahlen zum Stichtag nur aus damals veröffentlichten Jahresabschlüssen."""
    if not f: return {}
    g = lambda k: stand(f.get(k, []), tag)
    out = {}
    (um, um0), (ge, _), (bt, _), (br, _), (ek, _), (bi, _), (vb, _), (oc, _), (cx, _), (ak, _) = g('umsatz'), g('gewinn'), g('betrieb'), g('brutto'), g('eigenkapital'), g('bilanz'), g('verbind'), g('ocf'), g('capex'), g('aktien')
    v = lambda r: None if r is None else float(r[2])
    if v(ge) is not None and v(ek) and v(ek) > 0: out['roe'] = v(ge) / v(ek)
    if v(um) and v(um) > 0:
        if v(bt) is not None: out['opm'] = v(bt) / v(um)
        if v(br) is not None: out['gpm'] = v(br) / v(um)
        if um0 is not None and v(um0) and v(um0) > 0: out['wachstum'] = v(um) / v(um0) - 1
    cap = v(ak) * kurs if ak and v(ak) else None
    if cap and cap > 0:
        if v(ge) is not None: out['ep'] = v(ge) / cap
        if v(oc) is not None: out['fcfy'] = (v(oc) - (v(cx) or 0)) / cap
    if v(bi) and v(bi) > 0:
        if v(vb) is not None: out['schulden'] = v(vb) / v(bi)
        elif v(ek) is not None: out['schulden'] = 1 - v(ek) / v(bi)
        if v(ge) is not None and v(oc) is not None: out['accruals'] = (v(ge) - v(oc)) / v(bi)
    return out

def _beta(a, b):
    m = ~(np.isnan(a) | np.isnan(b))
    if m.sum() < 150 or np.var(b[m]) == 0: return None
    return float(np.cov(a[m], b[m])[0, 1] / np.var(b[m], ddof=1))

def faktoren(zeilen, bench_dict, tage, fund=None):
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
    br_ = np.array([x if x is not None else np.nan for x in bench], float)
    lb = np.diff(np.log(br_), prepend=np.nan)
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
            'beta': _beta(lr[i - 251:i + 1], lb[i - 251:i + 1]),
            'volspike': float(v[i - 4:i + 1].mean() / max(v[i - 49:i + 1].mean(), 1)), 'punkte': float(sc['punkte']),
        }
        if fund: f.update(fundamental(fund, d, c[i]))
        for k, x in enumerate(sc['kriterien']): f['r%d' % (k + 1)] = 1.0 if x['ok'] else 0.0
        for hk, hd in HOR.items():
            f['f' + hk] = (c[i + hd] / c[i] - 1) * 100 if i + hd < n else None
            if i + hd < n and not np.isnan(br_[i + hd]) and f['beta'] is not None:   # Rendite minus Beta mal Marktrendite (Beta nur aus der Vergangenheit)
                f['g' + hk] = f['f' + hk] - f['beta'] * (br_[i + hd] / br_[i] - 1) * 100
            else:
                f['g' + hk] = None
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

def auswerten(zeit, vor='f'):
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
                y = np.array([a[t][vor + hk] if a[t].get(vor + hk) is not None else np.nan for t in a], float)
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

_sperre = threading.Lock(); _letzter = [0.0]

def sec_holen(cik, ua):
    with _sperre:                                    # höchstens etwa 8 Abrufe pro Sekunde (SEC-Grenze 10)
        w = _letzter[0] + 0.13 - time.time()
        if w > 0: time.sleep(w)
        _letzter[0] = time.time()
    return json.loads(web(SEC % cik, ua).decode('utf-8'))

def main():
    liste = tickerliste()
    if len(sys.argv) > 1: liste = liste[:int(sys.argv[1])]
    ua = 'Reiseblog Faktortest %s' % os.environ.get('SEC_KONTAKT', 'kontakt@example.com')
    print('Aktien in der Liste:', len(liste))
    _, spy = trend.holen(BENCH[UNI], '10y')
    bd = {datum(z[0]): z[4] for z in spy}
    tage = [datum(spy[i][0]) for i in monatsende([datum(z[0]) for z in spy]) if i >= 253]
    print('Monatsenden:', len(tage), tage[0], '…', tage[-1])
    def hole(p):
        t, cik = p
        err, z, fund = None, None, None
        for v in range(3):
            try:
                z = trend.holen(t, '10y')[1]; break
            except Exception as e:
                time.sleep(2 * (v + 1)); err = e
        if z is None: print(t, 'Kursfehler:', err); return t, None, None
        for v in range(2 if cik else 0):
            try:
                fund = sec_kompakt(sec_holen(cik, ua)); break
            except Exception as e:
                time.sleep(2); err = e
        if fund is None and cik: print(t, 'SEC-Fehler:', err)
        return t, z, fund
    zeit, ok, mitfund = {}, 0, 0
    with ThreadPoolExecutor(6) as ex:
        for t, z, fund in ex.map(hole, liste):
            if not z or len(z) < 400: continue
            try:
                f = faktoren(z, bd, tage, fund)
            except Exception as e:
                print(t, 'Rechenfehler:', e); continue
            for d, v in f.items(): zeit.setdefault(d, {})[t] = v
            ok += 1; mitfund += 1 if fund else 0
            if ok % 50 == 0: print(ok, 'Aktien gerechnet, davon mit SEC-Daten', mitfund)
    if ok < len(liste) * 0.6: print('Zu wenige Aktien (%d), nichts geschrieben' % ok); sys.exit(1)
    res, adj = auswerten(zeit, 'f'), auswerten(zeit, 'g')
    faktoren_out = []
    def eintrag(k, name, besch, art):
        return {'id': k, 'name': name, 'beschreibung': besch, 'art': art, 'horizonte': res[k], 'urteil': gesamturteil(res[k]),
                'horizonte_adj': adj[k], 'urteil_adj': gesamturteil(adj[k])}
    for k, (name, besch) in KAND.items(): faktoren_out.append(eintrag(k, name, besch, 'kandidat'))
    for k in range(1, 13): faktoren_out.append(eintrag('r%d' % k, REGELN[k - 1], 'WCJ-Regel %d (ja/nein)' % k, 'regel'))
    out = {'universum': UNI, 'universum_name': UNI_NAMEN.get(UNI, UNI), 'vergleich': BENCH[UNI], 'stand': datetime.date.today().isoformat(), 'aktien': ok, 'aktien_mit_sec': mitfund, 'monate': len(zeit), 'von': tage[0], 'bis': tage[-1], 'teilung': TEILUNG,
           'hinweis': 'Rückblick, keine Prognose. Heutige Index-Mitglieder (Überlebensverzerrung), keine Kosten. Bei vielen Tests sind einzelne Zufallstreffer zu erwarten. "adj" = Rendite minus Beta mal Marktrendite (Beta nur aus Vergangenheit). Kennzahlen aus Jahresabschlüssen erst ab Meldedatum.',
           'faktoren': faktoren_out, 'regelkorrelation': korrelation(zeit), 'regelnamen': REGELN}
    json.dump(out, open(PFAD, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('geschrieben', PFAD, {u: sum(1 for f in faktoren_out if f['urteil'] == u) for u in ('traegt', 'dreht', 'unklar', 'nicht')},
          'bereinigt', {u: sum(1 for f in faktoren_out if f['urteil_adj'] == u) for u in ('traegt', 'dreht', 'unklar', 'nicht')})

if __name__ == '__main__':
    main()
