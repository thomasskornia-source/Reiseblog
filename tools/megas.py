#!/usr/bin/env python3
"""Megas: Unternehmen mit mehr als 1 Billion US-Dollar Börsenwert, laufendes Jahr (YTD) -> data/megas.json

Kein Token-Verbrauch, läuft täglich in der GitHub-Aktion „Top 10 S&P 500“ (nach tools/screener.py).
  Kurse:        Yahoo-Finance-Tageskurse (inoffiziell), Aktiensplits werden herausgerechnet.
  Aktienzahl:   SEC-Meldungen (dei:EntityCommonStockSharesOutstanding, sonst gewichtete verwässerte Aktienzahl),
                jeweils die zum Tag zuletzt veröffentlichte Zahl.
  Börsenwert:   Kurs (ohne Splits, wie damals) x Aktienzahl.
  KGV:          Kurs / Gewinn je Aktie der letzten vier Quartale (verwässert, aus den SEC-Quartalszahlen; Q4 = Jahr minus Q1 bis Q3).
                Nur Gewinn zum Tag der Veröffentlichung, kein Blick in die Zukunft. Negativer Gewinn = kein KGV.
Kandidaten stehen in KANDIDATEN; aufgenommen wird, wer am letzten Handelstag mindestens 1 Billion USD wert ist.
Aufruf:  SEC_KONTAKT=<mailadresse> python3 tools/megas.py
"""
import datetime, json, os, sys, time, urllib.parse, urllib.request
sys.path.insert(0, os.path.dirname(__file__))
import trend

ROOT = os.path.join(os.path.dirname(__file__), '..')
KANDIDATEN = ['NVDA', 'MSFT', 'AAPL', 'GOOGL', 'AMZN', 'META', 'AVGO', 'TSLA', 'LLY', 'WMT', 'JPM', 'ORCL', 'V', 'NFLX', 'MA', 'XOM', 'COST', 'PLTR']
SCHWELLE = 1e12

def web(url, ua):
    for k in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': ua}), timeout=60) as r:
                return r.read()
        except Exception:
            if k == 2: raise
            time.sleep(2)

def kurse(t):
    """(Tage dd.mm.yy, Kurs wie damals, Kurs ohne Splits-Effekt) seit Jahresbeginn (inkl. letztem Schlusskurs des Vorjahres als Basis)."""
    url = 'https://query1.finance.yahoo.com/v8/finance/chart/%s?range=2y&interval=1d&events=splits' % urllib.parse.quote(t)
    j = json.loads(web(url, 'Mozilla/5.0'))
    res = j['chart']['result'][0]
    close = res['indicators']['quote'][0]['close']
    splits = sorted(((int(k), v['numerator'] / v['denominator']) for k, v in (res.get('events', {}).get('splits') or {}).items()))
    zeilen = []
    for ts, c in zip(res['timestamp'], close):
        if c is None: continue
        faktor = 1.0
        for st, r in splits:
            if st > ts: faktor *= r          # später erfolgte Splits: Kurs vergleichbar machen
        zeilen.append((datetime.datetime.utcfromtimestamp(ts).date(), c, c / faktor))
    return zeilen

def aktien_reihe(d):
    """Liste (veröffentlicht, Aktienzahl) aufsteigend."""
    f = d['facts']
    pkt = {}
    for x in f.get('dei', {}).get('EntityCommonStockSharesOutstanding', {}).get('units', {}).get('shares', []):
        pkt.setdefault((x['accn'], x['end']), [x['filed'], 0])[1] += x['val']       # mehrere Aktiengattungen addieren
    if not pkt:
        for x in f.get('us-gaap', {}).get('WeightedAverageNumberOfDilutedSharesOutstanding', {}).get('units', {}).get('shares', []):
            if x.get('form') in ('10-Q', '10-K'):
                a, b = datetime.date.fromisoformat(x['start']), datetime.date.fromisoformat(x['end'])
                if 80 <= (b - a).days <= 100: pkt[(x['accn'], x['end'])] = [x['filed'], x['val']]
    return sorted((datetime.date.fromisoformat(a), v) for a, v in pkt.values())

def eps_quartale(d):
    """Quartals-Gewinn je Aktie (verwässert): Liste (Quartalsende, erstmals veröffentlicht, Wert), Q4 aus Jahr minus Q1 bis Q3."""
    daten = d['facts'].get('us-gaap', {}).get('EarningsPerShareDiluted', {}).get('units', {}).get('USD/shares', [])
    per = {}
    for x in daten:
        a, b = datetime.date.fromisoformat(x['start']), datetime.date.fromisoformat(x['end'])
        n = (b - a).days
        art = 'q' if 80 <= n <= 100 else 'j' if 350 <= n <= 380 else None
        if not art: continue
        k = (art, a, b); fl = datetime.date.fromisoformat(x['filed'])
        if k not in per: per[k] = {'erst': fl, 'neu': fl, 'val': x['val']}
        else:
            per[k]['erst'] = min(per[k]['erst'], fl)
            if fl >= per[k]['neu']: per[k]['neu'] = fl; per[k]['val'] = x['val']      # zuletzt gemeldeter Wert (Splits angepasst)
    q = {k: v for k, v in per.items() if k[0] == 'q'}
    out = [(b, v['erst'], v['val']) for (_, a, b), v in q.items()]
    for (_, a, b), v in per.items():
        if v is None or _ != 'j': continue
        vor = [(bb, vv) for (aa, bb), vv in ((k[1:], v2) for k, v2 in q.items()) if a <= aa and bb < b - datetime.timedelta(days=20)]
        if len(vor) == 3 and not any(bb.month == b.month and abs((bb - b).days) < 20 for bb, _ in vor):
            out.append((b, v['erst'], v['val'] - sum(vv['val'] for _, vv in vor)))
    return sorted(set(out))

def ttm(eps, tag):
    """Summe der letzten vier Quartale, die am Tag schon veröffentlicht waren."""
    ok = sorted((e for e in eps if e[1] <= tag), key=lambda e: e[0])
    if len(ok) < 4: return None
    letzte = ok[-4:]
    if (letzte[-1][0] - letzte[0][0]).days > 300: return None   # Lücke in den Quartalen
    return sum(e[2] for e in letzte)

def main():
    kontakt = os.environ.get('SEC_KONTAKT', '').strip()
    if not kontakt: sys.exit('SEC_KONTAKT fehlt')
    ua = 'Reiseblog-Megas %s' % kontakt
    cik = {v['ticker']: v['cik_str'] for v in json.loads(web('https://www.sec.gov/files/company_tickers.json', ua)).values()}
    jahr = datetime.date.today().year
    firmen, namen = [], {v['ticker']: v['title'] for v in json.loads(web('https://www.sec.gov/files/company_tickers.json', ua)).values()}
    for t in KANDIDATEN:
        try:
            z = kurse(t)
            if not z: continue
            aktien = None
            d = json.loads(web('https://data.sec.gov/api/xbrl/companyfacts/CIK%010d.json' % cik[t], ua)); time.sleep(0.3)
            aktien = aktien_reihe(d); eps = eps_quartale(d)
            if not aktien: print('keine Aktienzahl für', t); continue
            def anzahl(tag):
                v = [a for a in aktien if a[0] <= tag]
                return (v[-1] if v else aktien[0])[1]
            letzter = z[-1]
            if letzter[1] * anzahl(letzter[0]) < SCHWELLE: print('unter 1 Bio.:', t, round(letzter[1] * anzahl(letzter[0]) / 1e12, 2)); continue
            basis = [x for x in z if x[0].year < jahr][-1]       # letzter Schlusskurs des Vorjahres als 0 Prozent
            ytd = [x for x in z if x[0].year == jahr]
            firmen.append({'t': t, 'name': namen.get(t, t).title() if namen.get(t, t).isupper() else namen.get(t, t),
                           'wert': [round(x[1] * anzahl(x[0]) / 1e9) for x in ytd],
                           'perf': [round((x[2] / basis[2] - 1) * 100, 2) for x in ytd],
                           'kgv': [(lambda e: round(x[2] / e, 1) if e and e > 0 and x[2] / e < 400 else None)(ttm(eps, x[0])) for x in ytd],
                           'tage': [x[0].strftime('%d.%m.%y') for x in ytd]})
        except Exception as e:
            print('FEHLER bei %s: %s' % (t, e))
    if len(firmen) < 3: sys.exit('zu wenige Megas, Datei bleibt unverändert')
    gemeinsam = sorted(set.intersection(*(set(f['tage']) for f in firmen)), key=lambda s: datetime.datetime.strptime(s, '%d.%m.%y'))
    for f in firmen:
        pos = {t: i for i, t in enumerate(f['tage'])}
        for k in ('wert', 'perf', 'kgv'): f[k] = [f[k][pos[t]] for t in gemeinsam]
        del f['tage']
        f['wert_heute'] = f['wert'][-1]; f['ytd'] = f['perf'][-1]; f['kgv_heute'] = f['kgv'][-1]
    firmen.sort(key=lambda f: -f['wert_heute'])
    out = {'stand': datetime.date.today().strftime('%d.%m.%Y'), 'schwelle_mrd': int(SCHWELLE / 1e9), 'tage': gemeinsam, 'firmen': firmen}
    with open(os.path.join(ROOT, 'data', 'megas.json'), 'w', encoding='utf-8') as fh:
        fh.write(json.dumps(out, ensure_ascii=False, separators=(',', ':')).replace('},{"t"', '},\n{"t"').replace('"firmen":[', '"firmen":[\n') + '\n')
    print('Megas:', ', '.join('%s %s Mrd, YTD %s %%, KGV %s' % (f['t'], f['wert_heute'], f['ytd'], f['kgv_heute']) for f in firmen))

main()
