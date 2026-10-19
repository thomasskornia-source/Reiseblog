#!/usr/bin/env python3
"""Presse-Aufmerksamkeit je Aktie (Thomas, 19.10.2026) -> data/presse.json, angezeigt auf stimmung.html.

Frage von Thomas: Hängt es mit der Kursreaktion zusammen, wie oft ein Unternehmen in der Presse vorkommt, und lässt sich daraus eine
sinnvolle Stimmung ableiten? Dies ist ein Messwerkzeug, kein Signal.

Aufruf:  python3 tools/presse.py     läuft täglich (presse.yml)
Quelle Presse: GDELT DOC 2.0 (frei, ohne Schlüssel): Zahl der Nachrichtenartikel pro Tag (englischsprachig, weltweit) und mittlerer Tonwert
(negativ bis positiv). GDELT liefert die letzten 90 Tage auf einmal, darum gibt es sofort eine Historie. Kurse: Yahoo-Chartabruf.
Aktien: die in data/beobachtung.json und data/top10.json öffentlich geführten Werte (das Depot steht nicht in diesen Listen als solches).
Je Aktie:
  anteil  heutige Aufmerksamkeit: Mittel der letzten 3 Tage gegen die 60 Tage davor (z-Wert)
  ton     Tonwert der letzten 3 Tage gegen sein Mittel (z-Wert)
  r_*     Zusammenhänge (Pearson) über die 90 Tage: gleicher Tag und Folgetag von Aufmerksamkeit/Ton gegen |Kursänderung| bzw. Kursänderung
  n       Zahl der Tage; |r| unter 2/sqrt(n) gilt als nicht belastbar (kein Zusammenhang erkennbar)
Zusätzlich gebündelt über alle Aktien (pool). Es wird nichts überschrieben, wenn weniger als die Hälfte der Aktien abrufbar war.
"""
import datetime, json, math, os, re, statistics, sys, time, urllib.parse, urllib.request

ROOT = os.path.join(os.path.dirname(__file__), '..')
PFAD = os.path.join(ROOT, 'data', 'presse.json')
UA = {'User-Agent': 'Mozilla/5.0 (compatible; reiseblog-presse)'}
PAUSE = 6.0   # GDELT erlaubt etwa eine Anfrage je 5 Sekunden
SUCHE = {     # Suchbegriffe, wo der Firmenname allein zu unscharf ist (GDELT-Abfragesyntax)
    'GOOGL': '(Google OR Alphabet) (Gemini OR Android OR Search OR earnings)', 'GOOG': '(Google OR Alphabet) (Gemini OR Android OR Search OR earnings)',
    'AMZN': 'Amazon (AWS OR Bezos OR Prime OR earnings)', 'INTC': 'Intel (chip OR chips OR foundry OR earnings OR Xeon)',
    'KO': '"Coca-Cola"', 'BRK-B': '"Berkshire Hathaway"', 'NVDA': 'Nvidia', 'TTWO': '("Take-Two" OR "Rockstar Games" OR "GTA VI")',
    'AAPL': 'Apple (iPhone OR earnings OR Cook)', 'MSFT': 'Microsoft (Azure OR earnings OR Nadella)', 'META': 'Meta (Facebook OR Zuckerberg OR earnings)',
    'TSLA': 'Tesla (Musk OR earnings OR EV)',
}

def holen(url, timeout=60):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode('utf-8', 'replace')

def tickerliste():
    out = {}
    for datei, schluessel in (('beobachtung.json', 'aktien'), ('top10.json', 'top10')):
        try:
            j = json.load(open(os.path.join(ROOT, 'data', datei), encoding='utf-8'))
            for x in j.get(schluessel, []):
                t = x.get('ticker')
                if t and t not in out: out[t] = x.get('name') or t
        except Exception as e:
            print('Liste', datei, 'Fehler:', e)
    return out

def begriff(t, name):
    if t in SUCHE: return SUCHE[t]
    n = re.sub(r'\(.*?\)', '', name)
    n = re.sub(r',?\s+(Inc\.?|Corporation|Corp\.?|Company|Co\.?|Ltd\.?|plc|Holdings|Group|Class [A-C])\b', '', n, flags=re.I)
    n = re.sub(r'^The\s+', '', n.strip(), flags=re.I).strip(' ,.')
    return '"%s"' % n if ' ' in n or '-' in n else n

def gdelt(q, modus):
    u = 'https://api.gdeltproject.org/api/v2/doc/doc?query=%s&mode=%s&timespan=90d&format=json' % (urllib.parse.quote(q + ' sourcelang:english'), modus)
    t = holen(u)
    j = json.loads(t)
    reihe = j['timeline'][0]['data']
    return {x['date'][:8]: x['value'] for x in reihe}   # 'JJJJMMTT' -> Wert

def yahoo(ticker):
    try:
        u = 'https://query1.finance.yahoo.com/v8/finance/chart/%s?range=6mo&interval=1d' % urllib.parse.quote(ticker)
        j = json.loads(holen(u))['chart']['result'][0]
        return {datetime.datetime.utcfromtimestamp(t).strftime('%Y%m%d'): c for t, c in zip(j['timestamp'], j['indicators']['quote'][0]['close']) if c is not None}
    except Exception as e:
        print('Yahoo', ticker, 'Fehler:', e); return {}

# ---- Rechnung (reine Funktionen, testbar) ---------------------------------------------------------------------------
def z_wert(reihe, letzte=3, vorher=60):
    """Mittel der letzten Tage gegen die davor liegenden, in Standardabweichungen."""
    if len(reihe) < letzte + 20: return None
    alt = reihe[-(letzte + vorher):-letzte]
    sd = statistics.pstdev(alt)
    if sd == 0: return None
    return (statistics.mean(reihe[-letzte:]) - statistics.mean(alt)) / sd

def korr(a, b):
    p = [(x, y) for x, y in zip(a, b) if x is not None and y is not None]
    if len(p) < 15: return None, len(p)
    xs, ys = [x for x, _ in p], [y for _, y in p]
    sx, sy = statistics.pstdev(xs), statistics.pstdev(ys)
    if sx == 0 or sy == 0: return None, len(p)
    mx, my = statistics.mean(xs), statistics.mean(ys)
    return sum((x - mx) * (y - my) for x, y in p) / len(p) / (sx * sy), len(p)

def verschieb(a, k):
    """Wert von gestern (k=1) neben dem von heute: a[i-k] an Stelle i."""
    return [None] * k + a[:-k] if k else a

def auswerten(tage, anzahl, ton, kurs):
    """tage: sortierte Datumsliste; anzahl/ton/kurs: dict Datum -> Wert. Liefert Kennzahlen oder None."""
    d = [t for t in tage if t in anzahl and t in kurs]
    if len(d) < 40: return None
    n = [anzahl[t] for t in d]
    tn = [ton.get(t) for t in d]
    c = [kurs[t] for t in d]
    ret = [None] + [(c[i] / c[i - 1] - 1) * 100 for i in range(1, len(c))]
    absr = [None if r is None else abs(r) for r in ret]
    # Aufmerksamkeit als Abweichung vom gleitenden 20-Tage-Schnitt (Ausreißer statt Dauerrauschen)
    nz = []
    for i in range(len(n)):
        if i < 20: nz.append(None); continue
        w = n[i - 20:i]; sd = statistics.pstdev(w)
        nz.append((n[i] - statistics.mean(w)) / sd if sd else None)
    tz = []
    tv = [x for x in tn if x is not None]
    mt = statistics.mean(tv) if tv else 0
    for x in tn: tz.append(None if x is None else x - mt)
    r = {}
    r['aufm_vol_gleich'], nn = korr(nz, absr)
    r['aufm_vol_folge'], _ = korr(verschieb(nz, 1), absr)
    r['ton_ret_gleich'], _ = korr(tz, ret)
    r['ton_ret_folge'], _ = korr(verschieb(tz, 1), ret)
    r['n'] = nn
    r['schwelle'] = round(2 / math.sqrt(nn), 2) if nn else None
    return {'r': {k: (round(v, 2) if isinstance(v, float) else v) for k, v in r.items()},
            'serie': {'d': d[-60:], 'n': n[-60:], 't': [None if x is None else round(x, 2) for x in tn[-60:]], 'c': [round(x, 2) for x in c[-60:]]},
            'aufm': None if z_wert(n) is None else round(z_wert(n), 2),
            'ton': None if len(tv) < 20 else round(z_wert([x for x in tn if x is not None]) or 0, 2),
            'artikel_heute': round(n[-1]), 'artikel_schnitt': round(statistics.mean(n[-60:]))}, nz, tz, ret

def main():
    liste = tickerliste()
    if not liste: print('Keine Aktienliste'); sys.exit(1)
    out, pool_nz, pool_abs, pool_tz, pool_ret, ok = {}, [], [], [], [], 0
    for t, name in liste.items():
        q = begriff(t, name)
        try:
            a = gdelt(q, 'timelinevolraw'); time.sleep(PAUSE)
            tn = gdelt(q, 'timelinetone'); time.sleep(PAUSE)
        except Exception as e:
            print('GDELT', t, q, 'Fehler:', e); time.sleep(PAUSE); continue
        k = yahoo(t)
        tage = sorted(set(a) & set(k))
        res = auswerten(tage, a, tn, k)
        if not res: print(t, 'zu wenig Daten'); continue
        ok += 1
        erg, nz, tz, ret = res
        erg.update({'name': name, 'suche': q})
        out[t] = erg
        pool_nz += nz; pool_tz += tz; pool_ret += ret; pool_abs += [None if r is None else abs(r) for r in ret]
    if ok < max(1, len(liste) // 2):
        print('Nur %d von %d Aktien abrufbar, nichts überschrieben' % (ok, len(liste))); sys.exit(0)
    pr = {}
    pr['aufm_vol_gleich'], nn = korr(pool_nz, pool_abs)
    pr['ton_ret_gleich'], _ = korr(pool_tz, pool_ret)
    pr['n'] = nn; pr['schwelle'] = round(2 / math.sqrt(nn), 2) if nn else None
    erg = {'stand': datetime.date.today().isoformat(), 'quelle': 'GDELT DOC 2.0 (Artikelzahl, Tonwert), Yahoo (Kurse)',
           'hinweis': 'Messwerkzeug, kein Handelssignal. Zusammenhänge unter der Schwelle sind nicht belastbar.',
           'pool': {k: (round(v, 3) if isinstance(v, float) else v) for k, v in pr.items()}, 'aktien': out}
    json.dump(erg, open(PFAD, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('geschrieben:', ok, 'Aktien')

if __name__ == '__main__':
    main()
