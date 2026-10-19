#!/usr/bin/env python3
"""Sentiment-Indikatoren (Thomas, 19.10.2026) -> data/sentiment.json, angezeigt auf stimmung.html neben Markus Kochs Einschätzung.

Aufruf:  python3 tools/sentiment.py     läuft werktags nach US-Börsenschluss (sentiment.yml)
Alles aus freien Quellen ohne Schlüssel. Jede Quelle ist einzeln abgesichert: fällt eine aus, bleibt der Indikator leer und der
Rest läuft weiter.
  VIX, VIX3M, RSP, SPY   Yahoo-Chartabruf (wie tools/trend.py)
  High-Yield-Spread      FRED, Serie BAMLH0A0HYM2 (Risikoaufschlag von Ramschanleihen)
  Put/Call (Gesamt)      Cboe, totalpc.csv (kann veraltet sein, dann Hinweis)
  Fear & Greed           CNN-Datenabruf (inoffiziell, kann ausfallen)
  NAAIM Exposure         naaim.org (Seite wird gelesen, nur mit strenger Prüfung; kann ausfallen)
Die Ampel (pfeil: hoch = stützt die Börse, runter = belastet, seitwaerts = neutral) folgt festen, offenen Schwellen (SCHWELLEN unten),
damit sie wie Kochs Pfeile lesbar ist. Gesamtwert = Mittel der Pfeile (−100 bis +100). Verlauf des Gesamtwerts: 90 Tage.
Keine Anlageberatung: Stimmung ist ein Gegen- und Begleitindikator, kein Signal für sich.
"""
import csv, datetime, io, json, os, re, statistics, sys, urllib.parse, urllib.request

ROOT = os.path.join(os.path.dirname(__file__), '..')
PFAD = os.path.join(ROOT, 'data', 'sentiment.json')
UA = {'User-Agent': 'Mozilla/5.0 (compatible; reiseblog-sentiment)'}
MAX_VERLAUF = 90

FEHLER = []
_print = print
def print(*a, **k):
    FEHLER.append(' '.join(str(x) for x in a)[:200]); _print(*a, **k)

def holen(url, timeout=40):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode('utf-8', 'replace')

def yahoo(ticker, rng='6mo'):
    """Liste [(Datum, Schlusskurs)] oder []"""
    try:
        u = 'https://query1.finance.yahoo.com/v8/finance/chart/%s?range=%s&interval=1d' % (urllib.parse.quote(ticker), rng)
        j = json.loads(holen(u))['chart']['result'][0]
        ts, cl = j['timestamp'], j['indicators']['quote'][0]['close']
        return [(datetime.datetime.utcfromtimestamp(t).strftime('%Y-%m-%d'), c) for t, c in zip(ts, cl) if c is not None]
    except Exception as e:
        print('Yahoo', ticker, 'Fehler:', e); return []

def fred(serie):
    try:
        t = holen('https://fred.stlouisfed.org/graph/fredgraph.csv?id=' + serie)
        out = []
        for z in list(csv.reader(io.StringIO(t)))[1:]:
            if len(z) >= 2 and z[1] not in ('', '.'):
                out.append((z[0], float(z[1])))
        return out
    except Exception as e:
        print('FRED', serie, 'Fehler:', e); return []

def putcall():
    try:
        t = holen('https://cdn.cboe.com/resources/options/volume_and_call_put_ratios/totalpc.csv')
        zeilen = list(csv.reader(io.StringIO(t)))
        k = next(i for i, z in enumerate(zeilen) if z and z[0].strip().upper() == 'DATE' or (z and any('P/C' in c.upper() for c in z)))
        kopf = [c.strip().upper() for c in zeilen[k]]
        ci = next(i for i, c in enumerate(kopf) if 'P/C' in c)
        out = []
        for z in zeilen[k + 1:]:
            if len(z) > ci and z[0].strip():
                try:
                    d = datetime.datetime.strptime(z[0].strip(), '%m/%d/%Y').strftime('%Y-%m-%d') if '/' in z[0] else z[0].strip()
                    out.append((d, float(z[ci])))
                except ValueError:
                    pass
        return out
    except Exception as e:
        print('Cboe Put/Call Fehler:', e); return []

def feargreed():
    try:
        j = json.loads(holen('https://production.dataviz.cnn.io/index/fearandgreed/graphdata'))
        h = j['fear_and_greed_historical']['data']
        out = [(datetime.datetime.utcfromtimestamp(x['x'] / 1000).strftime('%Y-%m-%d'), float(x['y'])) for x in h]
        return out
    except Exception as e:
        print('CNN Fear&Greed Fehler:', e); return []

def naaim():
    try:
        t = holen('https://naaim.org/programs/naaim-exposure-index/')
        m = re.search(r'(?:NAAIM\s+Number|Exposure\s+Index)[^0-9<]{0,120}(?:<[^>]*>\s*){0,6}(\d{1,3}\.\d{1,2})', t, re.I)
        if not m: return []
        v = float(m.group(1))
        if not (-50 <= v <= 200): return []
        return [(datetime.date.today().strftime('%Y-%m-%d'), v)]
    except Exception as e:
        print('NAAIM Fehler:', e); return []

# ---- Bewertung: reine Funktionen (testbar) --------------------------------------------------------------------------
SCHWELLEN = {
    'vix': (17.0, 25.0),          # unter 17 ruhig (hoch), über 25 Angst (runter)
    'kurve': (0.90, 1.00),        # VIX / VIX3M: unter 0,90 entspannt (hoch), über 1,00 Stress (runter)
    'hy': (3.5, 5.0),             # Prozent: unter 3,5 entspannt, über 5,0 Stress
    'breite': (0.0, -1.0),        # RSP/SPY gegen eigenen 50-Tage-Schnitt in Prozent: über 0 breit, unter −1 eng
    'pc': (0.70, 1.00),           # Put/Call: unter 0,70 sorglos (hoch), über 1,00 Angst (runter)
    'fg': (60.0, 40.0),           # CNN: über 60 Gier, unter 40 Angst
    'naaim': (80.0, 40.0),        # Fondsmanager: über 80 voll investiert, unter 40 vorsichtig
}

def pfeil_niedrig_gut(v, grenzen):
    a, b = grenzen
    return 'hoch' if v < a else 'runter' if v > b else 'seitwaerts'

def pfeil_hoch_gut(v, grenzen):
    a, b = grenzen
    return 'hoch' if v > a else 'runter' if v < b else 'seitwaerts'

def reihe(zeilen, n=60):
    return [round(v, 3) for _, v in zeilen[-n:]]

def bauen(daten):
    """daten: dict Name -> Liste [(Datum, Wert)]. Gibt die Indikatorliste zurück."""
    ind = []
    def add(i, name, wert, einheit, pfeil, text, erkl, quelle, url, rz, datum):
        ind.append({'id': i, 'name': name, 'wert': wert, 'einheit': einheit, 'pfeil': pfeil, 'text': text, 'erklaerung': erkl,
                    'quelle': quelle, 'url': url, 'reihe': rz, 'datum': datum})
    vix = daten.get('vix') or []
    if vix:
        d, v = vix[-1]
        add('vix', 'VIX (Angstbarometer)', round(v, 2), '', pfeil_niedrig_gut(v, SCHWELLEN['vix']),
            'ruhig' if v < SCHWELLEN['vix'][0] else 'Angst' if v > SCHWELLEN['vix'][1] else 'normal bis nervös',
            'Erwartete Schwankung des S&P 500 über 30 Tage aus Optionspreisen. Unter 17 ruhig, über 25 Angst. Sehr niedrige Werte bedeuten oft Sorglosigkeit.',
            'Cboe über Yahoo (^VIX)', 'https://finance.yahoo.com/quote/%5EVIX', reihe(vix), d)
    v3 = daten.get('vix3m') or []
    if vix and v3:
        m3 = dict(v3); par = [(d, v / m3[d]) for d, v in vix if d in m3 and m3[d]]
        if par:
            d, r = par[-1]
            add('kurve', 'VIX-Kurve (VIX / VIX3M)', round(r, 3), '', pfeil_niedrig_gut(r, SCHWELLEN['kurve']),
                'Stress (Kurve umgekehrt)' if r > SCHWELLEN['kurve'][1] else 'entspannt' if r < SCHWELLEN['kurve'][0] else 'neutral',
                'Verhältnis der Angst von heute zur Angst der nächsten drei Monate. Über 1,0 rechnen Anleger kurzfristig mit mehr Ausschlägen als später: ein Stresszeichen.',
                'Cboe über Yahoo (^VIX, ^VIX3M)', 'https://finance.yahoo.com/quote/%5EVIX3M', reihe(par), d)
    hy = daten.get('hy') or []
    if hy:
        d, v = hy[-1]
        add('hy', 'High-Yield-Spread', round(v, 2), ' %', pfeil_niedrig_gut(v, SCHWELLEN['hy']),
            'Stress' if v > SCHWELLEN['hy'][1] else 'entspannt' if v < SCHWELLEN['hy'][0] else 'normal',
            'Zusatzzins, den Ramschanleihen gegenüber Staatsanleihen zahlen. Steigt er, trauen Anleger Firmen weniger zu: oft ein Frühwarnzeichen für Aktien.',
            'FRED (ICE BofA US High Yield OAS)', 'https://fred.stlouisfed.org/series/BAMLH0A0HYM2', reihe(hy), d)
    rsp, spy = daten.get('rsp') or [], daten.get('spy') or []
    if rsp and spy:
        ms = dict(spy); q = [(d, v / ms[d]) for d, v in rsp if d in ms and ms[d]]
        if len(q) >= 50:
            d, r = q[-1]; m50 = statistics.mean(v for _, v in q[-50:]); abw = (r / m50 - 1) * 100
            add('breite', 'Marktbreite (RSP gegen SPY)', round(abw, 2), ' %', pfeil_hoch_gut(abw, SCHWELLEN['breite']),
                'breit getragen' if abw > SCHWELLEN['breite'][0] else 'eng (wenige Riesen tragen)' if abw < SCHWELLEN['breite'][1] else 'neutral',
                'Gleichgewichteter S&P 500 (RSP) gegen den marktgewichteten (SPY), Abweichung vom 50-Tage-Schnitt. Steigt RSP stärker, machen viele Aktien mit; fällt das Verhältnis, tragen wenige Riesen den Index.',
                'Yahoo (RSP, SPY)', 'https://finance.yahoo.com/quote/RSP', reihe(q), d)
    pc = daten.get('pc') or []
    if pc:
        d, v = pc[-1]
        add('pc', 'Put/Call-Verhältnis (Gesamt)', round(v, 2), '', pfeil_niedrig_gut(v, SCHWELLEN['pc']),
            'viel Absicherung / Angst' if v > SCHWELLEN['pc'][1] else 'sorglos' if v < SCHWELLEN['pc'][0] else 'normal',
            'Verhältnis gehandelter Verkaufsoptionen zu Kaufoptionen. Über 1,0 sichern sich viele ab; ganz extreme Werte gelten auch als Gegenindikator (zu viel Angst = Boden nah).',
            'Cboe', 'https://www.cboe.com/us/options/market_statistics/daily/', reihe(pc), d)
    fg = daten.get('fg') or []
    if fg:
        d, v = fg[-1]
        add('fg', 'Fear & Greed (CNN)', round(v), '', pfeil_hoch_gut(v, SCHWELLEN['fg']),
            'Gier' if v > SCHWELLEN['fg'][0] else 'Angst' if v < SCHWELLEN['fg'][1] else 'neutral',
            'Mischwert (0 bis 100) aus sieben Teilen: Kurs-Momentum, Marktbreite, Optionen, Junkbonds, Volatilität und mehr. Inoffizieller Abruf.',
            'CNN Business', 'https://edition.cnn.com/markets/fear-and-greed', reihe(fg), d)
    na = daten.get('naaim') or []
    if na:
        d, v = na[-1]
        add('naaim', 'NAAIM Exposure (Fondsmanager)', round(v, 1), '', pfeil_hoch_gut(v, SCHWELLEN['naaim']),
            'voll investiert' if v > SCHWELLEN['naaim'][0] else 'vorsichtig' if v < SCHWELLEN['naaim'][1] else 'neutral',
            'Durchschnittliche Aktienquote aktiver Fondsmanager (0 bis 100, kann darüber gehen). Sehr hohe Werte heißen: wer kaufen wollte, hat schon gekauft.',
            'NAAIM', 'https://naaim.org/programs/naaim-exposure-index/', [v], d)
    return ind

def gesamt(ind):
    w = {'hoch': 1, 'runter': -1, 'seitwaerts': 0}
    if not ind: return None
    s = round(100 * sum(w[i['pfeil']] for i in ind) / len(ind))
    pfeil = 'hoch' if s >= 30 else 'runter' if s <= -30 else 'seitwaerts'
    return {'score': s, 'pfeil': pfeil, 'anzahl': len(ind),
            'text': {'hoch': 'Die Stimmungsdaten stützen die Börse.', 'runter': 'Die Stimmungsdaten belasten die Börse.', 'seitwaerts': 'Die Stimmungsdaten sind gemischt.'}[pfeil]}

def main():
    daten = {'vix': yahoo('^VIX'), 'vix3m': yahoo('^VIX3M'), 'rsp': yahoo('RSP'), 'spy': yahoo('SPY'),
             'hy': fred('BAMLH0A0HYM2'), 'pc': putcall(), 'fg': feargreed(), 'naaim': naaim()}
    ind = bauen(daten)
    # Cboe-Datei kann veraltet sein: dann nicht als aktuell zeigen
    heute = datetime.date.today()
    for i in ind:
        try:
            alter = (heute - datetime.date.fromisoformat(i['datum'])).days
        except ValueError:
            alter = 0
        i['alter_tage'] = alter
        if alter > 10:
            i['veraltet'] = True
    frisch = [i for i in ind if not i.get('veraltet')]
    if len(frisch) < 3:
        print('Zu wenige frische Indikatoren (%d), nichts überschrieben' % len(frisch)); sys.exit(0)
    g = gesamt(frisch)
    alt = {}
    try:
        alt = json.load(open(PFAD, encoding='utf-8'))
    except Exception:
        pass
    verlauf = [x for x in alt.get('verlauf', []) if x.get('d') != heute.isoformat()]
    verlauf.append({'d': heute.isoformat(), 'score': g['score']})
    out = {'stand': heute.isoformat(), 'gesamt': g, 'indikatoren': ind, 'verlauf': verlauf[-MAX_VERLAUF:],
           'schwellen': SCHWELLEN, 'meldungen': FEHLER[:20],
           'hinweis': 'Eigene Auswertung freier Daten, keine Anlageberatung. Schwellen sind Faustregeln und keine Prognose.'}
    json.dump(out, open(PFAD, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('geschrieben:', len(ind), 'Indikatoren, Gesamt', g['score'])

if __name__ == '__main__':
    main()
