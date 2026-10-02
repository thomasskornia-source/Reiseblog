"""Trend-Logik für James im Aktien-Check (gemeinsam für Aktien und den S&P 500).

Linien: 8- und 21-Tage-EMA, 50- und 200-Tage-Durchschnitt. Der Verlauf für den Chart umfasst ein Jahr (252 Handelstage). Kursdaten: Yahoo-Finance-Tageskurse (inoffiziell, kostenlos).

Einordnung (Kurs = letzter Schlusskurs), von oben nach unten, die erste zutreffende Zeile gilt:
  unter 200                         -> Down   „unter der 200-Tage-Linie“
  über 8, 21 und 50                 -> Up     „über 8-, 21- und 50-Tage-Linie“
  über 8 und 21, aber unter 50      -> Medium „über 8 und 21, aber unter 50“
  unter 8, aber über 21             -> Medium „Rücksetzer: unter 8, über 21“
  unter 21, aber über 50            -> Medium „zwischen 21 und 50“ (der Markt weiß nicht wohin)
  unter 21 und unter 50 (200 hält)  -> Down   „unter 21- und 50-Tage-Linie, 200er hält“
"""
import datetime, json, os, re, sys, urllib.parse, urllib.request
sys.path.insert(0, os.path.dirname(__file__))
import muster

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

def rsi_reihe(c, n=14):
    """RSI nach Wilder."""
    out = [None] * len(c)
    if len(c) <= n: return out
    gew = [max(c[i] - c[i - 1], 0) for i in range(1, n + 1)]; verl = [max(c[i - 1] - c[i], 0) for i in range(1, n + 1)]
    g, v = sum(gew) / n, sum(verl) / n
    out[n] = 100 - 100 / (1 + g / v) if v else 100
    for i in range(n + 1, len(c)):
        d = c[i] - c[i - 1]
        g = (g * (n - 1) + max(d, 0)) / n; v = (v * (n - 1) + max(-d, 0)) / n
        out[i] = 100 - 100 / (1 + g / v) if v else 100
    return out

def macd_reihen(c):
    """MACD (12, 26, 9): Linie, Signal, Histogramm."""
    e12, e26 = ema_reihe(c, 12), ema_reihe(c, 26)
    linie = [None if a is None or b is None else a - b for a, b in zip(e12, e26)]
    erste = next(i for i, x in enumerate(linie) if x is not None)
    sig = ema_reihe([x for x in linie if x is not None], 9)
    signal = [None] * erste + sig
    return linie, signal

def wochen_ema(zeilen, n=10):
    """EMA der Wochenschlusskurse (aktuelle Woche mit dem letzten Kurs)."""
    woche = {}
    for z in zeilen:
        d = datetime.datetime.utcfromtimestamp(z[0]).isocalendar()
        woche[(d[0], d[1])] = z[4]
    reihe = ema_reihe(list(woche.values()), n)
    return reihe[-1]

def score(zeilen, c, m8, m21, m50, m200, rsi, macd, signal, benchmark):
    """Eigener Setup-Score mit 12 offenen Regeln (angelehnt an Chart-Scanner, kein Nachbau eines fremden Scores)."""
    h = [z[2] for z in zeilen]; l = [z[3] for z in zeilen]; v = [z[5] for z in zeilen]; n = len(c)
    kurs = c[-1]
    tr = [max(h[i] - l[i], abs(h[i] - c[i - 1]), abs(l[i] - c[i - 1])) for i in range(1, n)]
    atr = sma_reihe(tr, 14)
    atr100 = [x for x in atr[-100:] if x is not None]
    sma20 = sum(c[-20:]) / 20; sd = (sum((x - sma20) ** 2 for x in c[-20:]) / 20) ** 0.5
    e20 = ema_reihe(c, 20)[-1]; atr20 = sum(tr[-20:]) / 20
    squeeze = (sma20 + 2 * sd < e20 + 1.5 * atr20) and (sma20 - 2 * sd > e20 - 1.5 * atr20)
    atr_enge = bool(atr100) and atr[-1] <= 0.8 * (sum(atr100) / len(atr100))
    obv = [0]
    for i in range(1, n): obv.append(obv[-1] + (v[i] if c[i] > c[i - 1] else -v[i] if c[i] < c[i - 1] else 0))
    obv_steigt = obv[-1] > obv[-21] and obv[-1] > sum(obv[-20:]) / 20
    auf = sum(v[i] for i in range(n - 50, n) if c[i] > c[i - 1]); ab = sum(v[i] for i in range(n - 50, n) if c[i] < c[i - 1])
    ud = auf / ab if ab else 9
    nr7 = (h[-1] - l[-1]) <= min(h[i] - l[i] for i in range(n - 7, n))
    vdu = (sum(v[-5:]) / 5) <= 0.7 * (sum(v[-50:]) / 50)
    tiefs = muster.wendepunkte(l, 'tief'); hochs = muster.wendepunkte(h, 'hoch')
    hhhl = len(tiefs) >= 2 and len(hochs) >= 2 and tiefs[-1][1] > tiefs[-2][1] and hochs[-1][1] > hochs[-2][1]
    wema = wochen_ema(zeilen, 10)
    hoch52 = max(h[-252:])
    rs = None
    if benchmark and len(benchmark) > 64:
        rs = (kurs / c[-64] - 1) - (benchmark[-1] / benchmark[-64] - 1)
    k = [
        ('Trend', 'Kurs über 8, 21 und 50, geordnet (MA FAN)', kurs > m8 > m21 > m50, None),
        ('Trend', 'über der 200er, und sie steigt', kurs > m200 and m200 > sma_reihe(c, 200)[-21], None),
        ('Trend', 'über dem 10-Wochen-EMA', wema is not None and kurs > wema, None),
        ('Trend', 'höhere Hochs und höhere Tiefs', hhhl, None),
        ('Stärke', 'höchstens 5 % unter dem 52-Wochen-Hoch', kurs >= hoch52 * 0.95, None),
        ('Stärke', 'besser als der S&P 500 (3 Monate)', rs is not None and rs > 0, None if rs is None else '%+.1f Punkte' % (rs * 100)),
        ('Momentum', 'RSI(14) zwischen 50 und 75', rsi is not None and 50 <= rsi <= 75, None if rsi is None else '%.0f' % rsi),
        ('Momentum', 'MACD über der Signallinie', macd is not None and signal is not None and macd > signal, None),
        ('Volumen', 'mehr Umsatz an Auf- als an Abtagen (50 Tage)', ud > 1.1, '%.2f' % ud),
        ('Volumen', 'On-Balance-Volume steigt', obv_steigt, None),
        ('Spannung', 'Squeeze oder verengte Schwankung (ATR)', squeeze or atr_enge, None),
        ('Spannung', 'NR7 oder Umsatz trocknet aus (VDU)', nr7 or vdu, None),
    ]
    punkte = sum(1 for x in k if x[2])
    stufe = 'Stark' if punkte >= 9 else 'Momentum im Aufbau' if punkte >= 6 else 'Beobachten' if punkte >= 4 else 'Schwach'
    return {'punkte': punkte, 'von': 12, 'stufe': stufe,
            'kriterien': [{'gruppe': a, 'name': b, 'ok': bool(ok), **({'wert': w} if w else {})} for a, b, ok, w in k]}

def analyse(zeilen, meta=None, tage=252, benchmark=None, mit_score=True):
    c = [z[4] for z in zeilen]
    if len(c) < 210: raise ValueError('zu wenig Kursverlauf (%d Tage)' % len(c))
    m8, m21, m50, m200 = ema_reihe(c, 8), ema_reihe(c, 21), sma_reihe(c, 50), sma_reihe(c, 200)
    rsi = rsi_reihe(c); mlinie, msignal = macd_reihen(c)
    kurs = c[-1]
    ampel, zone = einordnen(kurs, m8[-1], m21[-1], m50[-1], m200[-1])
    r = lambda x: round(x, 2)
    letzte = range(len(zeilen) - tage, len(zeilen))
    fenster = list(letzte)
    mus = muster.erkennen([zeilen[i][2] for i in fenster], [zeilen[i][3] for i in fenster], [zeilen[i][4] for i in fenster])
    out = {
        'stand': datetime.datetime.utcfromtimestamp(zeilen[-1][0]).strftime('%d.%m.%Y'),
        'waehrung': (meta or {}).get('currency'),
        'kurs': r(kurs), 'ma8': r(m8[-1]), 'ma21': r(m21[-1]), 'ma50': r(m50[-1]), 'ma200': r(m200[-1]),
        'abstand_pct': round((kurs / m200[-1] - 1) * 100, 1),
        'ma200_steigt': m200[-1] > m200[-21],
        'hoch_52w': r(max(c[-252:])), 'tief_52w': r(min(c[-252:])),
        'pos_52w_pct': round((kurs - min(c[-252:])) / (max(c[-252:]) - min(c[-252:])) * 100) if max(c[-252:]) > min(c[-252:]) else 50,
        'ampel': ampel, 'lage': zone,
        'rsi': round(rsi[-1], 1), 'macd': round(mlinie[-1], 2), 'macd_signal': round(msignal[-1], 2),
        'macd_hist': round(mlinie[-1] - msignal[-1], 2), 'muster': mus,
        'serie': {
            'd': [datetime.datetime.utcfromtimestamp(zeilen[i][0]).strftime('%d.%m.%y') for i in letzte],
            'o': [r(zeilen[i][1]) for i in letzte], 'h': [r(zeilen[i][2]) for i in letzte],
            'l': [r(zeilen[i][3]) for i in letzte], 'c': [r(zeilen[i][4]) for i in letzte],
            'v': [int(zeilen[i][5] / 1000) for i in letzte],
            'm8': [r(m8[i]) for i in letzte], 'm21': [r(m21[i]) for i in letzte],
            'm50': [r(m50[i]) for i in letzte], 'm200': [r(m200[i]) for i in letzte],
        },
    }
    if mit_score:
        out['score'] = score(zeilen, c, m8[-1], m21[-1], m50[-1], m200[-1], rsi[-1], mlinie[-1], msignal[-1], benchmark)
    return out

def kompakt(text):
    """Zahlenlisten in einer Zeile halten, damit die JSON-Dateien lesbar und klein bleiben."""
    return re.sub(r'\[\s*((?:-?[\d.]+(?:e[-+]?\d+)?,?\s*|"[^"]*",?\s*)+)\]',
                  lambda m: '[' + re.sub(r'\s*\n\s*', ' ', m.group(1)).strip() + ']', text)
