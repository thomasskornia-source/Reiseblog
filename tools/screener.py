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

DETAIL = ('serie', 'muster', 'ma8', 'ma21', 'ma50', 'ma200', 'ma200_steigt', 'macd', 'macd_signal', 'hoch_52w', 'tief_52w', 'kreuz', 'kreuz_kurz', 'score')
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
                'rsi': a['rsi'], 'abstand_pct': a['abstand_pct'], 'pos_52w_pct': a['pos_52w_pct'], '_a': a}
    except Exception:
        return None

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
    bm = [z[4] for z in trend.holen('^GSPC')[1]]
    z = None
    try: z = sec_zahlen()
    except Exception as e: print('SEC-Zahlen nicht abrufbar:', e)
    with ThreadPoolExecutor(8) as ex: js = list(ex.map(lambda f: james(f, bm), fl))
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
           'top10': top, 'sektoren': dict(sorted(sektoren.items()))}
    with open(pfad, 'w', encoding='utf-8') as fh:
        fh.write(trend.kompakt(json.dumps(out, ensure_ascii=False, indent=1)) + '\n')
    beobachten(bm)
    print('Geprüft: %d, Top 10: %s' % (len(alle), ', '.join('%s (%.2f)' % (t['ticker'], t['rang']) for t in top)))

main()
