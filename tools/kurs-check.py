#!/usr/bin/env python3
"""Kurs gegen gleitende Durchschnitte (für James im Aktien-Check).

Aufruf:  python3 tools/kurs-check.py KO          (US-Ticker)
         python3 tools/kurs-check.py SIE.DE      (Xetra: .DE, London: .L, Paris: .PA …)
Quelle: Yahoo-Finance-Kursdaten (täglich, 2 Jahre, nicht offiziell, kostenlos). Gibt JSON aus.
Fehler (kein Kurs, zu wenig Verlauf): Exit-Code 1 und eine Zeile "FEHLER: …" – dann keine Zahlen erfinden.
"""
import json, sys, urllib.request, urllib.parse, datetime

def holen(ticker):
    url = 'https://query1.finance.yahoo.com/v8/finance/chart/%s?range=2y&interval=1d' % urllib.parse.quote(ticker)
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, timeout=30) as r:
        j = json.load(r)
    res = j['chart']['result'][0]
    q = res['indicators']['quote'][0]
    reihe = [(t, c) for t, c in zip(res['timestamp'], q['close']) if c is not None]
    return res['meta'], reihe

def sma(w, n):
    return sum(w[-n:]) / n if len(w) >= n else None

def ema(w, n):
    k = 2 / (n + 1); e = sum(w[:n]) / n
    for x in w[n:]: e = x * k + e * (1 - k)
    return e

def main():
    if len(sys.argv) != 2: sys.exit(__doc__)
    t = sys.argv[1].strip().upper()
    try:
        meta, reihe = holen(t)
    except Exception as e:
        print('FEHLER: Kursdaten für %s nicht abrufbar (%s)' % (t, e)); sys.exit(1)
    c = [x for _, x in reihe]
    if len(c) < 210:
        print('FEHLER: zu wenig Kursverlauf für %s (%d Tage)' % (t, len(c))); sys.exit(1)
    kurs = c[-1]; m200 = sma(c, 200); m50 = sma(c, 50); e21 = ema(c, 21)
    m200_vor = sum(c[-220:-20]) / 200
    tage_ueber = sum(1 for i in range(1, 61) if c[-i] > sum(c[-i - 199:len(c) - i + 1]) / 200)
    if kurs > m200 * 1.03: lage = 'deutlich über'
    elif kurs >= m200: lage = 'knapp über'
    elif kurs >= m200 * 0.97: lage = 'knapp unter'
    else: lage = 'deutlich unter'
    out = {
        'ticker': t, 'waehrung': meta.get('currency'),
        'stand': datetime.datetime.utcfromtimestamp(reihe[-1][0]).strftime('%d.%m.%Y'),
        'kurs': round(kurs, 2), 'ma200': round(m200, 2), 'abstand_ma200_pct': round((kurs / m200 - 1) * 100, 1),
        'lage': lage, 'ma200_steigt': m200 > m200_vor, 'tage_ueber_ma200_von_60': tage_ueber,
        'ma50': round(m50, 2), 'ema21': round(e21, 2),
        'hoch_52w': round(max(c[-252:]), 2), 'tief_52w': round(min(c[-252:]), 2),
        'quelle': 'Yahoo Finance (Tageskurse)'
    }
    print(json.dumps(out, ensure_ascii=False, indent=2))

main()
