#!/usr/bin/env python3
"""Top-10-Vorauswahl aus dem S&P 500 für WCJ (läuft täglich per GitHub-Aktion, kostet keine Claude-Token).

James: Trend und Setup-Score aus tools/trend.py (Yahoo-Tageskurse).
Warren: sieben einfache Qualitäts- und Preisregeln aus den Jahreszahlen der US-Börsenaufsicht SEC
        (XBRL-„Frames“: je Kennzahl ein Abruf für alle Firmen, rund 15 Abrufe insgesamt).
Rang = je zur Hälfte Anteil erfüllter Warren-Regeln und James-Score (von 12); Aktien „unter der 200-Tage-Linie“ fallen heraus.

Aufruf:  SEC_KONTAKT=<mailadresse> python3 tools/screener.py     schreibt data/top10.json und data/beobachtung.json (eigene Aktien, nur James' Ampel)
Die SEC verlangt in der Kennung des Abrufs eine Kontaktadresse (Umgebungsvariable SEC_KONTAKT, in GitHub als Secret hinterlegt).
Ohne SEC_KONTAKT oder bei SEC-Fehler: Rang nur nach James' Trend (Vermerk „warren“: false in der Datei).
"""
import csv, datetime, io, json, os, sys, time, urllib.request
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0, os.path.dirname(__file__))
import trend, insider

DETAIL = ('serie', 'muster', 'ma8', 'ma21', 'ma50', 'ma200', 'ma200_steigt', 'macd', 'macd_signal', 'hoch_52w', 'tief_52w', 'kreuz', 'kreuz_kurz', 'woche', 'score')
ROOT = os.path.join(os.path.dirname(__file__), '..')
LISTE = 'https://raw.githubusercontent.com/datasets/s-and-p-500-companies/main/data/constituents.csv'
SEC = 'https://data.sec.gov/api/xbrl/frames/us-gaap/%s/%s/%s.json'

def web(url, ua):
    req = urllib.request.Request(url, headers={'User-Agent': ua})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read()

def firmen():
    rows = csv.DictReader(io.StringIO(web(LISTE, 'Mozilla/5.0').decode('utf-8')))
    return [{'t': r['Symbol'], 'name': r['Security'], 'sektor': r['GICS Sector'], 'cik': int(r['CIK'])} for r in rows]

def frame(ua, tag, einheit, periode):
    try:
        d = json.loads(web(SEC % (tag, einheit, periode), ua))
    except Exception:
        return {}
    time.sleep(0.2)   # weit unter der SEC-Grenze (10 Abrufe pro Sekunde)
    return {x['cik']: x['val'] for x in d['data']}

def sec_zahlen():
    kontakt = os.environ.get('SEC_KONTAKT', '').strip()
    if not kontakt: return None
    ua = 'Reiseblog-Screener %s' % kontakt
    jahr = datetime.date.today().year - 1
    ni = frame(ua, 'NetIncomeLoss', 'USD', 'CY%d' % jahr)
    if len(ni) < 1000:                      # Jahr noch nicht komplett veröffentlicht
        jahr -= 1; ni = frame(ua, 'NetIncomeLoss', 'USD', 'CY%d' % jahr)
    if len(ni) < 1000: return None
    z = {'jahr': jahr, 'ni': [frame(ua, 'NetIncomeLoss', 'USD', 'CY%d' % (jahr - k)) for k in range(4, 0, -1)] + [ni]}
    z['eps'] = frame(ua, 'EarningsPerShareDiluted', 'USD-per-shares', 'CY%d' % jahr)
    z['eigenkapital'] = frame(ua, 'StockholdersEquity', 'USD', 'CY%dQ4I' % jahr)
    z['schulden'] = frame(ua, 'LongTermDebt', 'USD', 'CY%dQ4I' % jahr)
    for cik, v in frame(ua, 'LongTermDebtNoncurrent', 'USD', 'CY%dQ4I' % jahr).items(): z['schulden'].setdefault(cik, v)
    z['ocf'] = frame(ua, 'NetCashProvidedByUsedInOperatingActivities', 'USD', 'CY%d' % jahr)
    z['capex'] = frame(ua, 'PaymentsToAcquirePropertyPlantAndEquipment', 'USD', 'CY%d' % jahr)
    z['umsatz'] = frame(ua, 'Revenues', 'USD', 'CY%d' % jahr)
    for cik, v in frame(ua, 'RevenueFromContractWithCustomerExcludingAssessedTax', 'USD', 'CY%d' % jahr).items(): z['umsatz'].setdefault(cik, v)
    return z

def warren(f, kurs, z):
    """Sieben Regeln: je True / False / None (None = Daten fehlen oder Regel passt nicht, zählt nicht mit)."""
    cik = f['cik']; bank = f['sektor'] == 'Financials'
    reihe = [m.get(cik) for m in z['ni']]; ni = reihe[-1]
    eigen, umsatz, eps = z['eigenkapital'].get(cik), z['umsatz'].get(cik), z['eps'].get(cik)
    r = []
    bekannt = [x for x in reihe if x is not None]
    r.append(('Gewinn in jedem der letzten 5 Jahre', all(x > 0 for x in bekannt) if len(bekannt) >= 4 else None))
    r.append(('Gewinn höher als vor 4 Jahren', (reihe[-1] > reihe[0]) if None not in (reihe[0], reihe[-1]) and reihe[0] > 0 else None))
    roe = ni / eigen if ni is not None and eigen and eigen > 0 else None
    r.append(('Eigenkapitalrendite mindestens 15 %', roe >= 0.15 if roe is not None else None))
    marge = ni / umsatz if ni is not None and umsatz else None
    r.append(('Nettomarge mindestens 10 %', marge >= 0.10 if marge is not None else None))
    sch = z['schulden'].get(cik)
    if bank or ni is None: r.append(('Schulden höchstens das 4-Fache des Jahresgewinns', None))
    else: r.append(('Schulden höchstens das 4-Fache des Jahresgewinns', (ni > 0 and (sch or 0) <= 4 * ni)))
    ocf, capex = z['ocf'].get(cik), z['capex'].get(cik)
    r.append(('Freier Cashflow positiv', (ocf - (capex or 0)) > 0 if ocf is not None and not bank else None))
    kgv = kurs / eps if eps and eps > 0 else None
    r.append(('KGV zwischen 0 und 25', (kgv <= 25) if kgv is not None else (False if eps is not None else None)))
    return r, (round(kgv, 1) if kgv else None), (round(roe * 100) if roe is not None else None), (round(marge * 100) if marge is not None else None)

def james(f, bm):
    try:
        meta, zeilen = trend.holen(f['t'].replace('.', '-'))
        a = trend.analyse(zeilen, meta, benchmark=bm)
        return {'kurs': a['kurs'], 'ampel': a['ampel'], 'lage': a['lage'], 'punkte': a['score']['punkte'], 'stufe': a['score']['stufe'],
                'rsi': a['rsi'], 'abstand_pct': a['abstand_pct'], 'pos_52w_pct': a['pos_52w_pct'], '_a': a, '_h': verlauf(zeilen)}
    except Exception:
        return None

def verlauf(zeilen):
    c = [z[4] for z in zeilen]
    return {'d': [datetime.datetime.utcfromtimestamp(z[0]).strftime('%d.%m.%y') for z in zeilen], 'c': c,
            'm8': trend.ema_reihe(c, 8), 'm21': trend.ema_reihe(c, 21), 'm50': trend.sma_reihe(c, 50), 'm200': trend.sma_reihe(c, 200)}

SEKTOR_NAMEN = {'Communication Services': 'Kommunikation', 'Consumer Discretionary': 'Konsum (zyklisch)', 'Consumer Staples': 'Basiskonsum',
                'Energy': 'Energie', 'Financials': 'Finanzen', 'Health Care': 'Gesundheit', 'Industrials': 'Industrie',
                'Information Technology': 'Technologie', 'Materials': 'Rohstoffe', 'Real Estate': 'Immobilien', 'Utilities': 'Versorger'}

def sektor_rotation(fl, js, sp_zeilen):
    """Sektor-Rotation: je GICS-Sektor die Beliebtheit (0-100) über das letzte Jahr, aus den Kursen aller S&P-500-Aktien (gleich gewichtet).
    Beliebtheit (5 Tage geglättet) = Mittel aus Rangplatz (unter den 11 Sektoren) von: Stärke gegenüber dem S&P 500 über 1 Monat (21 Tage, Median der Aktien),
    über 3 Monate (63 Tage) und Anteil der Aktien über ihrer 21-Tage-Linie. Der Verlauf wird jedes Mal aus den Kursen neu berechnet
    (Rückrechnung), zusätzlich wird der Tageswert in data/sektoren-archiv.json fortgeschrieben (für Zeiträume über ein Jahr hinaus)."""
    sp = verlauf(sp_zeilen); tage = sp['d'][-252:]
    nach = {}
    for f, j in zip(fl, js):
        if not j: continue
        h = j['_h']; nach.setdefault(f['sektor'], []).append((h, {d: i for i, d in enumerate(h['d'])}))
    if len(nach) < 8: return None
    spp = {d: i for i, d in enumerate(sp['d'])}
    med = lambda x: sorted(x)[len(x) // 2]
    roh = {k: [] for k in nach}   # je Sektor: Liste (rs1, rs3, b21, b50) je Tag
    for d in tage:
        t = spp[d]; s1 = sp['c'][t] / sp['c'][t - 21] - 1; s3 = sp['c'][t] / sp['c'][t - 63] - 1
        for k, lst in nach.items():
            r1, r3, b21, b50 = [], [], 0, 0; n = 0
            for h, pos in lst:
                i = pos.get(d)
                if i is None or i < 63 or h['m21'][i] is None or h['m50'][i] is None: continue
                n += 1; r1.append(h['c'][i] / h['c'][i - 21] - 1); r3.append(h['c'][i] / h['c'][i - 63] - 1)
                b21 += h['c'][i] > h['m21'][i]; b50 += h['c'][i] > h['m50'][i]
            roh[k].append(((med(r1) - s1) * 100, (med(r3) - s3) * 100, 100 * b21 / n, 100 * b50 / n, n) if n >= 5 else None)
    namen = list(nach); score = {k: [] for k in namen}
    pr = lambda x, alle: 100 * sum(1 for y in alle if y < x) / max(1, len(alle) - 1)
    for ti in range(len(tage)):
        werte = {k: roh[k][ti] for k in namen if roh[k][ti]}
        if len(werte) < 8:
            for k in namen: score[k].append(score[k][-1] if score[k] else 50)
            continue
        for k in namen:
            w = werte.get(k)
            if not w: score[k].append(score[k][-1] if score[k] else 50); continue
            a1 = [v[0] for v in werte.values()]; a3 = [v[1] for v in werte.values()]; ab = [v[2] for v in werte.values()]
            score[k].append(round(0.35 * pr(w[0], a1) + 0.35 * pr(w[1], a3) + 0.30 * pr(w[2], ab)))
    for k in namen:   # 5-Tage-Glättung: Rangplätze springen täglich, der Verlauf soll lesbar sein
        sc = score[k]; score[k] = [round(sum(sc[max(0, i - 4):i + 1]) / len(sc[max(0, i - 4):i + 1])) for i in range(len(sc))]
    liste = []
    for k in namen:
        sc = score[k]; last = sc[-1]; vor10 = sc[-11]; slope = last - vor10
        status = ('kuehlt' if slope <= -10 and vor10 >= 50 else 'heiss' if last >= 70 else 'interessant' if slope >= 10 else 'kalt' if last < 35 else 'ruhig')
        w = roh[k][-1] or (0, 0, 0, 0, 0)
        liste.append({'sektor': k, 'name': SEKTOR_NAMEN.get(k, k), 'aktien': w[4], 'score': last, 'delta10': slope, 'status': status,
                      'rs1m': round(w[0], 1), 'rs3m': round(w[1], 1), 'ueber21': round(w[2]), 'ueber50': round(w[3]), 'verlauf': sc})
    liste.sort(key=lambda x: (-x['score'], -x['delta10']))
    for r, x in enumerate(liste): x['rang'] = r + 1
    for x in liste:   # Rang vor 20 Handelstagen
        alle = sorted(liste, key=lambda y: -y['verlauf'][-21]); x['rang_vor20'] = [y['sektor'] for y in alle].index(x['sektor']) + 1
    heute = datetime.date.today().strftime('%d.%m.%Y')
    out = {'stand': heute, 'tage': tage, 'sektoren': liste}
    with open(os.path.join(ROOT, 'data', 'sektoren.json'), 'w', encoding='utf-8') as fh:
        fh.write(trend.kompakt(json.dumps(out, ensure_ascii=False, indent=1)) + '\n')
    pfad = os.path.join(ROOT, 'data', 'sektoren-archiv.json')
    try: arch = json.load(open(pfad, encoding='utf-8'))
    except Exception: arch = {'verlauf': []}
    arch['verlauf'] = [v for v in arch['verlauf'] if v['datum'] != heute] + [{'datum': heute, 'score': {x['sektor']: x['score'] for x in liste}}]
    with open(pfad, 'w', encoding='utf-8') as fh:
        fh.write(json.dumps({'verlauf': arch['verlauf'][-1500:]}, ensure_ascii=False).replace('},', '},\n') + '\n')
    return out

MEGA = ('AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'META', 'TSLA')

def breite(js, fl=None, sp_z=None):
    """Marktbreite: Anteil der S&P-500-Aktien über ihrer 8-, 21-, 50- und 200-Tage-Linie (alle Werte mit Kursdaten), Verlauf in data/breite.json."""
    a = [j['_a'] for j in js if j]
    if len(a) < 100: return
    pro = lambda k: round(100 * sum(1 for x in a if x['kurs'] > x[k]) / len(a))
    heute = datetime.date.today().strftime('%d.%m.%Y')
    pfad = os.path.join(ROOT, 'data', 'breite.json')
    try: d = json.load(open(pfad, encoding='utf-8'))
    except Exception: d = {'verlauf': []}
    verl = []
    if sp_z:   # Verlauf über das letzte Jahr aus den Kursen zurückgerechnet (heutige Indexmitglieder, kein Archiv nötig)
        sp = verlauf(sp_z); lst = [(j['_h'], {x: i for i, x in enumerate(j['_h']['d'])}) for j in js if j]
        for dd in sp['d'][-252:]:
            z = {'m8': [0, 0], 'm21': [0, 0], 'm50': [0, 0], 'm200': [0, 0]}
            for h, pos in lst:
                i = pos.get(dd)
                if i is None: continue
                for k in z:
                    if h[k][i] is not None: z[k][1] += 1; z[k][0] += h['c'][i] > h[k][i]
            if min(v[1] for v in z.values()) >= 100:
                verl.append({'datum': dd, 'ueber8': round(100 * z['m8'][0] / z['m8'][1]), 'ueber21': round(100 * z['m21'][0] / z['m21'][1]),
                             'ueber50': round(100 * z['m50'][0] / z['m50'][1]), 'ueber200': round(100 * z['m200'][0] / z['m200'][1])})
    if len(verl) < 100: verl = [v for v in d.get('verlauf', []) if v['datum'] != heute] + [{'datum': heute, 'ueber8': pro('ma8'), 'ueber21': pro('ma21'), 'ueber50': pro('ma50'), 'ueber200': pro('ma200')}]
    verlauf_liste = verl[-260:]
    mega = []
    for f, j in zip(fl or [], js):   # die sieben größten Werte: über dem 8-Tage-EMA? (James zählt, wie viele der Megacaps stark sind)
        if j and f['t'] in MEGA:
            x = j['_a']; mega.append({'t': f['t'], 'name': f['name'], 'ueber8': x['kurs'] > x['ma8'], 'ueber21': x['kurs'] > x['ma21'], 'abstand8_pct': round((x['kurs'] / x['ma8'] - 1) * 100, 1)})
    mega.sort(key=lambda m: MEGA.index(m['t']))
    with open(pfad, 'w', encoding='utf-8') as fh:
        fh.write(json.dumps({'stand': heute, 'n': len(a), 'megacaps': mega, 'verlauf': verlauf_liste}, ensure_ascii=False, indent=None).replace('},', '},\n') + '\n')

def universum(fl, js):
    """Alle S&P-500-Aktien in Kurzform (Kurs, Ampel, Lage, kleiner Verlauf) -> data/universum.json, für die Watchlist auf der Seite (ohne Token)."""
    heute = datetime.date.today().strftime('%d.%m.%Y'); liste = []
    for f, j in zip(fl, js):
        if not j: continue
        c = j['_h']['c'][-41:]
        if len(c) < 5: continue
        lo, hi = min(c), max(c); sp = [round(100 * (x - lo) / (hi - lo)) if hi > lo else 50 for x in c]
        liste.append({'t': f['t'], 'n': f['name'], 's': f['sektor'], 'k': round(j['kurs'], 2), 'a': j['ampel'], 'p': j['punkte'], 'l': j['lage'],
                      'd1': round((c[-1] / c[-2] - 1) * 100, 2), 'sp': sp})
    liste.sort(key=lambda x: x['t'])
    with open(os.path.join(ROOT, 'data', 'universum.json'), 'w', encoding='utf-8') as fh:
        fh.write(json.dumps({'stand': heute, 'aktien': liste}, ensure_ascii=False, separators=(',', ':')).replace('},{', '},\n{') + '\n')

def beobachten(bm):
    """Eigene Aktien aus data/aktien.json: James' Ampel täglich neu (ohne Texte, ohne Token) -> data/beobachtung.json."""
    try: eintraege = json.load(open(os.path.join(ROOT, 'data', 'aktien.json'), encoding='utf-8'))['einschaetzungen']
    except Exception: return
    pfad = os.path.join(ROOT, 'data', 'beobachtung.json')
    try: alt = {x['ticker']: x for x in json.load(open(pfad, encoding='utf-8')).get('aktien', [])}
    except Exception: alt = {}
    heute = datetime.date.today().strftime('%d.%m.%Y')
    liste = []
    for e in eintraege:
        sym = (e.get('symbol') or str(e.get('ticker', '')).split(' ')[0]).upper()
        j = james({'t': sym}, bm)
        if not j: continue
        v = alt.get(sym, {})
        vorher = v.get('ampel') if v.get('stand') != heute else v.get('ampel_vorher')
        a = j['_a']
        liste.append({'ticker': sym, 'name': e.get('name', sym), 'kurs': j['kurs'], 'ampel': j['ampel'], 'lage': j['lage'], 'punkte': j['punkte'],
                      'rsi': j['rsi'], 'abstand_pct': j['abstand_pct'], 'pos_52w_pct': j['pos_52w_pct'],
                      'detail': {k: a[k] for k in DETAIL if k in a}, 'ampel_vorher': vorher, 'stand': heute})
    with open(pfad, 'w', encoding='utf-8') as fh:
        fh.write(trend.kompakt(json.dumps({'stand': heute, 'aktien': liste}, ensure_ascii=False, indent=1)) + '\n')

def main():
    fl = firmen()
    sp_z = trend.holen('^GSPC')[1]
    bm = [z[4] for z in sp_z]
    z = None
    try: z = sec_zahlen()
    except Exception as e: print('SEC-Zahlen nicht abrufbar:', e)
    with ThreadPoolExecutor(8) as ex: js = list(ex.map(lambda f: james(f, bm), fl))
    breite(js, fl, sp_z)
    universum(fl, js)
    sek = sektor_rotation(fl, js, sp_z)
    alle = []
    for f, j in zip(fl, js):
        if not j: continue
        w, kgv, roe, marge = (warren(f, j['kurs'], z) if z else ([], None, None, None))
        ok = sum(1 for _, v in w if v is True); n = sum(1 for _, v in w if v is not None)
        if z and n < 4: continue            # zu wenig Zahlen für ein Urteil
        wp = ok / n if n else 0
        rang = (0.5 * wp + 0.5 * j['punkte'] / 12) if z else j['punkte'] / 12
        alle.append({'ticker': f['t'], 'cik': f['cik'], 'name': f['name'], 'sektor': f['sektor'], **{k: v for k, v in j.items() if k != '_a'}, '_a': j['_a'], 'warren_ok': ok, 'warren_von': n,
                     'kgv': kgv, 'roe_pct': roe, 'marge_pct': marge,
                     'warren_gut': [t for t, v in w if v is True], 'warren_fehlt': [t for t, v in w if v is False], 'rang': round(rang, 3)})
    kandidaten = sorted((a for a in alle if a['ampel'] != 'Down'), key=lambda a: -a['rang'])
    top = kandidaten[:10]
    pfad = os.path.join(ROOT, 'data', 'top10.json')
    try: alt = json.load(open(pfad, encoding='utf-8'))
    except Exception: alt = {}
    vorher = [t['ticker'] for t in alt.get('top10', [])]
    if alt.get('stand') == datetime.date.today().strftime('%d.%m.%Y'): vorher = alt.get('vorher', vorher)
    for i, t in enumerate(top): t['platz'] = i + 1; t['neu'] = bool(vorher) and t['ticker'] not in vorher
    for t in top:   # Detail für die Aufklapp-Ansicht (Chart und Chartanalyse), nur für die Top 10
        a = t['_a']
        t['detail'] = {k: a[k] for k in DETAIL if k in a}
    kontakt = os.environ.get('SEC_KONTAKT', '').strip()
    for t in top:   # Insiderkäufe (Form 4, 90 Tage) und Datum der letzten Zahlen aus den SEC-Meldungen
        if not kontakt: break
        try: t.update(insider.holen(t['cik'], kontakt))
        except Exception as e: print('Insider-Daten fehlen für %s: %s' % (t['ticker'], e))
    for t in alle: t.pop('_a', None)
    kurz = ('ticker', 'name', 'ampel', 'lage', 'kgv', 'roe_pct', 'marge_pct', 'rsi', 'abstand_pct', 'pos_52w_pct', 'warren_gut', 'warren_fehlt', 'warren_ok', 'warren_von', 'punkte')
    sektoren = {}
    for a in kandidaten:
        liste = sektoren.setdefault(a['sektor'], [])
        if len(liste) < 5: liste.append({k: a[k] for k in kurz})
    for t in top: t.pop('cik', None)
    heute = [t['ticker'] for t in top]
    out = {'stand': datetime.date.today().strftime('%d.%m.%Y'), 'warren': bool(z), 'zahlenjahr': z['jahr'] if z else None,
           'geprueft': len(alle), 'ohne_down': len(kandidaten), 'vorher': vorher, 'raus': [t for t in vorher if t not in heute],
           'top10': top, 'sektoren': dict(sorted(sektoren.items())),
           'sektor_reihenfolge': [{'sektor': x['sektor'], 'status': x['status'], 'score': x['score']} for x in (sek['sektoren'] if sek else [])]}
    with open(pfad, 'w', encoding='utf-8') as fh:
        fh.write(trend.kompakt(json.dumps(out, ensure_ascii=False, indent=1)) + '\n')
    beobachten(bm)
    print('Geprüft: %d, Top 10: %s' % (len(alle), ', '.join('%s (%.2f)' % (t['ticker'], t['rang']) for t in top)))

main()
