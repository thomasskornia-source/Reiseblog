"""Trend-Logik für James im Aktien-Check (gemeinsam für Aktien und den S&P 500).

Linien: 8- und 21-Tage-EMA, 50- und 200-Tage-Durchschnitt. Kursdaten: Yahoo-Finance-Tageskurse (inoffiziell, kostenlos).

Einordnung (Kurs = letzter Schlusskurs), von oben nach unten, die erste zutreffende Zeile gilt:
  unter 200                         -> Down   „unter der 200-Tage-Linie“
  über 8, 21 und 50                 -> Up     „über 8-, 21- und 50-Tage-Linie“
  über 8 und 21, aber unter 50      -> Medium „über 8 und 21, aber unter 50“
  unter 8, aber über 21             -> Medium „Rücksetzer: unter 8, über 21“
  unter 21, aber über 50            -> Medium „zwischen 21 und 50“ (der Markt weiß nicht wohin)
  unter 21 und unter 50 (200 hält)  -> Down   „unter 21- und 50-Tage-Linie, 200er hält“
"""
import datetime, json, re, urllib.parse, urllib.request

def holen(ticker, rng='2y'):
    url = 'https://query1.finance.yahoo.com/v8/finance/chart/%s?range=%s&interval=1d' % (urllib.parse.quote(ticker), rng)
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, timeout=30) as r:
        j = json.load(r)
    res = j['chart']['result'][0]
    q = res['indicators']['quote'][0]
    zeilen = []
    for i, t in enumerate(res['timestamp']):
        o, h, l, c, v = (q[k][i] for k in ('open', 'high', 'low', 'close', 'volume'))
        if None in (o, h, l, c): continue
        zeilen.append((t, o, h, l, c, v or 0))
    return res['meta'], zeilen

def sma_reihe(w, n):
    return [None if i + 1 < n else sum(w[i + 1 - n:i + 1]) / n for i in range(len(w))]

def ema_reihe(w, n):
    k = 2 / (n + 1); out = [None] * len(w)
    if len(w) < n: return out
    e = sum(w[:n]) / n; out[n - 1] = e
    for i in range(n, len(w)):
        e = w[i] * k + e * (1 - k); out[i] = e
    return out

def einordnen(kurs, m8, m21, m50, m200):
    if kurs < m200: return 'Down', 'unter der 200-Tage-Linie'
    if kurs >= m8 and kurs >= m21 and kurs >= m50: return 'Up', 'über 8-, 21- und 50-Tage-Linie'
    if kurs >= m8 and kurs >= m21: return 'Medium', 'über 8 und 21, aber unter 50'
    if kurs >= m21: return 'Medium', 'Rücksetzer: unter 8, über 21'
    if kurs >= m50: return 'Medium', 'zwischen 21 und 50'
    return 'Down', 'unter 21- und 50-Tage-Linie, 200er hält'

def analyse(zeilen, meta=None, tage=80):
    c = [z[4] for z in zeilen]
    if len(c) < 210: raise ValueError('zu wenig Kursverlauf (%d Tage)' % len(c))
    m8, m21, m50, m200 = ema_reihe(c, 8), ema_reihe(c, 21), sma_reihe(c, 50), sma_reihe(c, 200)
    kurs = c[-1]
    ampel, zone = einordnen(kurs, m8[-1], m21[-1], m50[-1], m200[-1])
    r = lambda x: round(x, 2)
    letzte = range(len(zeilen) - tage, len(zeilen))
    return {
        'stand': datetime.datetime.utcfromtimestamp(zeilen[-1][0]).strftime('%d.%m.%Y'),
        'waehrung': (meta or {}).get('currency'),
        'kurs': r(kurs), 'ma8': r(m8[-1]), 'ma21': r(m21[-1]), 'ma50': r(m50[-1]), 'ma200': r(m200[-1]),
        'abstand_pct': round((kurs / m200[-1] - 1) * 100, 1),
        'ma200_steigt': m200[-1] > m200[-21],
        'hoch_52w': r(max(c[-252:])), 'tief_52w': r(min(c[-252:])),
        'ampel': ampel, 'lage': zone,
        'serie': {
            'd': [datetime.datetime.utcfromtimestamp(zeilen[i][0]).strftime('%d.%m.%y') for i in letzte],
            'o': [r(zeilen[i][1]) for i in letzte], 'h': [r(zeilen[i][2]) for i in letzte],
            'l': [r(zeilen[i][3]) for i in letzte], 'c': [r(zeilen[i][4]) for i in letzte],
            'v': [int(zeilen[i][5] / 1000) for i in letzte],
            'm8': [r(m8[i]) for i in letzte], 'm21': [r(m21[i]) for i in letzte],
            'm50': [r(m50[i]) for i in letzte], 'm200': [r(m200[i]) for i in letzte],
        },
    }

def kompakt(text):
    """Zahlenlisten in einer Zeile halten, damit die JSON-Dateien lesbar und klein bleiben."""
    return re.sub(r'\[\s*((?:-?[\d.]+(?:e[-+]?\d+)?,?\s*|"[^"]*",?\s*)+)\]',
                  lambda m: '[' + re.sub(r'\s*\n\s*', ' ', m.group(1)).strip() + ']', text)
