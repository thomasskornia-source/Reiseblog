#!/usr/bin/env python3
"""Option Flows (Näherung) für James im Aktien-Check.

Aufruf:  python3 tools/optionsfluesse.py KO              (nur US-Aktien mit börsengehandelten Optionen; BRK.B und BRK-B gehen beide)
         python3 tools/optionsfluesse.py KO --schreibe   trägt Richtung und Text in den Eintrag in data/aktien.json ein
                                                         (james.flows) und merkt sich den Tageswert in data/flows/KO.json
Quelle: öffentliche, verzögerte Optionsdaten der Cboe (cdn.cboe.com, kostenlos, inoffizielle Schnittstelle):
alle Kontrakte mit Tagesvolumen, offenen Positionen (Open Interest), Geld-/Briefkurs und letztem Preis.
Bewertung auf Jahresbasis: put_call_relativ = heutiges Put/Call-Volumen geteilt durch das Put/Call-Verhältnis der
offenen Positionen. Es wird mit den eigenen Tageswerten der Aktie aus den letzten bis zu 252 Handelstagen verglichen
(data/flows/<Ticker>.json, gesammelt von tools/flows-sammeln.py): im untersten Fünftel = bullisch (heute ungewöhnlich
call-lastig), im obersten Fünftel = bärisch, dazwischen neutral. Solange weniger als 40 Tageswerte vorliegen, gilt
ersatzweise bis 0,65 bullisch, ab 1,4 bärisch; das Feld `basis` sagt, was gilt.
Ausgabe: JSON. Fehler (kein US-Ticker, keine Optionen, nicht abrufbar): Exit-Code 1, Zeile "FEHLER: …" – dann
keine Option Flows angeben („keine Daten“), nichts schätzen.

WICHTIG, ehrlich einordnen: Das ist KEIN echter Institutionen-Flow. Die Daten zeigen, WO heute Umsatz war
(Calls oder Puts, Prämie, ungewöhnlich hohes Volumen gegenüber den offenen Positionen), aber nicht, ob gekauft oder
verkauft wurde und von wem. Bezahlanbieter (z. B. Unusual Whales, FlowAlgo) liefern Käufer-/Verkäuferseite, Sweeps
und Blocks; das fehlt hier.
"""
import datetime, json, os, re, sys, urllib.request

VERLAUF_ORDNER = os.path.join(os.path.dirname(__file__), '..', 'data', 'flows')
AKTIEN = os.path.join(os.path.dirname(__file__), '..', 'data', 'aktien.json')
MIN_TAGE, MAX_TAGE = 40, 252

class Fehler(Exception):
    pass

def holen(sym):
    url = 'https://cdn.cboe.com/api/global/delayed_quotes/options/%s.json' % sym
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)

def normal(ticker):
    sym = ticker.strip().upper().replace('-', '.')   # Yahoo schreibt BRK-B, die Cboe BRK.B
    if not re.fullmatch(r'[A-Z]{1,5}(\.[A-Z])?', sym):
        raise Fehler('%s ist kein US-Ticker (nur US-Aktien haben hier Optionsdaten)' % sym)
    return sym

def verlauf_pfad(sym):
    return os.path.join(VERLAUF_ORDNER, sym.replace('.', '-') + '.json')

def verlauf_lesen(sym):
    try:
        with open(verlauf_pfad(sym), encoding='utf-8') as f:
            return json.load(f).get('verlauf', [])
    except (OSError, ValueError):
        return []

def verlauf_speichern(sym, out):
    """Ein Tageswert je Handelstag (gleicher Tag wird überschrieben), höchstens 252 Tage."""
    if out.get('put_call_relativ') is None: return
    tag = (out.get('stand') or '')[:10]
    if not tag: return
    v = [x for x in verlauf_lesen(sym) if x.get('d') != tag]
    v.append({'d': tag, 'rel': out['put_call_relativ'], 'pc': out['put_call_volumen'],
              'cp': out['call_praemie_usd'], 'pp': out['put_praemie_usd']})
    v = sorted(v, key=lambda x: x['d'])[-MAX_TAGE:]
    os.makedirs(VERLAUF_ORDNER, exist_ok=True)
    with open(verlauf_pfad(sym), 'w', encoding='utf-8') as f:
        f.write('{"symbol": "%s", "verlauf": [\n%s\n]}\n' % (sym, ',\n'.join(json.dumps(x, ensure_ascii=False) for x in v)))

def auswerten(ticker):
    sym = normal(ticker)
    try:
        j = holen(sym)
    except Exception as e:
        raise Fehler('keine Optionsdaten für %s (%s)' % (sym, e))
    d = j.get('data', {}); opts = d.get('options') or []
    heute = datetime.date.today()
    kurs = d.get('current_price')
    zeilen = []
    for o in opts:
        m = re.fullmatch(r'([A-Z]+)(\d{6})([CP])(\d{8})', o.get('option', ''))
        if not m or m.group(1) != sym.replace('.', ''): continue   # Kontrakte heißen BRKB…, nicht BRK.B…
        vol = o.get('volume') or 0; oi = o.get('open_interest') or 0
        bid, ask, last = o.get('bid') or 0, o.get('ask') or 0, o.get('last_trade_price') or 0
        preis = (bid + ask) / 2 if ask else last
        verfall = datetime.datetime.strptime(m.group(2), '%y%m%d').date()
        strike = int(m.group(4)) / 1000
        zeilen.append(dict(art=m.group(3), strike=strike, verfall=verfall, vol=vol, oi=oi,
                           praemie=vol * preis * 100, dte=(verfall - heute).days,
                           otm=(strike > kurs) if m.group(3) == 'C' else (strike < kurs) if kurs else None,
                           name=o['option']))
    if not zeilen:
        raise Fehler('keine Optionskontrakte für %s gefunden' % sym)
    def summe(art, f=lambda z: True, feld='vol'):
        return sum(z[feld] for z in zeilen if z['art'] == art and f(z))
    cv, pv = summe('C'), summe('P')
    cp, pp = summe('C', feld='praemie'), summe('P', feld='praemie')
    coi, poi = summe('C', feld='oi'), summe('P', feld='oi')
    gesamt_p = cp + pp
    anteil_c = cp / gesamt_p if gesamt_p else None
    kurz_c = summe('C', lambda z: z['dte'] <= 30, 'praemie'); kurz_p = summe('P', lambda z: z['dte'] <= 30, 'praemie')
    otm_c = summe('C', lambda z: z['otm'], 'praemie')
    auff = sorted([z for z in zeilen if z['vol'] >= 300 and z['oi'] and z['vol'] > z['oi'] and z['praemie'] >= 100000],
                  key=lambda z: -z['praemie'])[:5]
    # Calls haben immer mehr Umsatz und Prämie als Puts (Stillhalter, höhere Preise). Darum zählt nicht das Put/Call-
    # Volumen allein, sondern sein Verhältnis zum Put/Call-Verhältnis der offenen Positionen (Normalwert der Aktie).
    rel = (pv / cv) / (poi / coi) if cv and coi and poi else None
    stand = j.get('timestamp') or ''
    out = {
        'symbol': sym, 'quelle': 'Cboe verzögerte Optionsdaten', 'stand': stand,
        'call_volumen': int(cv), 'put_volumen': int(pv), 'put_call_volumen': round(pv / cv, 2) if cv else None,
        'put_call_open_interest': round(poi / coi, 2) if coi else None,
        'put_call_relativ': round(rel, 2) if rel is not None else None,
        'call_praemie_usd': int(cp), 'put_praemie_usd': int(pp),
        'call_praemie_anteil_pct': round(anteil_c * 100) if anteil_c is not None else None,
        'otm_call_praemie_anteil_an_calls_pct': round(otm_c / cp * 100) if cp else None,
        'kurzlaufend_30d_call_praemie_usd': int(kurz_c), 'kurzlaufend_30d_put_praemie_usd': int(kurz_p),
        'iv30_pct': d.get('iv30'),
        'auffaellig': [dict(kontrakt=z['name'], art='Call' if z['art'] == 'C' else 'Put', strike=z['strike'],
                            verfall=z['verfall'].isoformat(), volumen=int(z['vol']), open_interest=int(z['oi']),
                            praemie_usd=int(z['praemie'])) for z in auff],
        'hinweis': 'Näherung aus Umsatz und Prämie des Tages. Käufer- oder Verkäuferseite ist nicht erkennbar; Absicherung '
                   'und Stillhalter-Geschäfte sind möglich.'
    }
    # Bewertung auf Jahresbasis (eigene Tageswerte der Aktie), sonst ersatzweise feste Schwellen
    hist = [x['rel'] for x in verlauf_lesen(sym) if x.get('d') != stand[:10] and x.get('rel') is not None][-MAX_TAGE:]
    if gesamt_p < 500000 or (cv + pv) < 1000 or rel is None:
        richtung, stark, basis = 'neutral', 'gering (wenig Umsatz)', 'zu wenig Umsatz für eine Aussage'
    elif len(hist) >= MIN_TAGE:
        anteil = sum(1 for x in hist if x <= rel) / len(hist)
        richtung = 'bullisch' if anteil <= 0.2 else 'bärisch' if anteil >= 0.8 else 'neutral'
        stark = 'mittel'
        basis = 'Vergleich mit den eigenen letzten %d Handelstagen (heute höher als %d %% davon)' % (len(hist), round(anteil * 100))
        out['verlauf_tage'] = len(hist); out['rang_pct'] = round(anteil * 100)
    else:
        richtung = 'bullisch' if rel <= 0.65 else 'bärisch' if rel >= 1.4 else 'neutral'
        stark = 'mittel'
        basis = 'Vergleich mit den offenen Positionen; der Jahresvergleich folgt (bisher %d von %d Tageswerten gesammelt)' % (len(hist) + 1, MIN_TAGE)
        out['verlauf_tage'] = len(hist) + 1
    out.update({'richtung': richtung, 'aussagekraft': stark, 'basis': basis})
    return out

def de(x, n=2):
    return ('%.*f' % (n, x)).replace('.', ',')

def text(o):
    t = 'Put/Call-Volumen %s (Normalwert %s), rund %s %% der Prämie in Calls (ca. %s Mio. $ gegen %s Mio. $ bei Puts)' % (
        de(o['put_call_volumen']), de(o['put_call_open_interest']), o['call_praemie_anteil_pct'],
        de(o['call_praemie_usd'] / 1e6, 1), de(o['put_praemie_usd'] / 1e6, 1))
    if o['auffaellig']:
        a = o['auffaellig'][0]
        t += '; auffälligster Kontrakt: %s %s mit Verfall %s (ca. %s Mio. $ Prämie)' % (
            a['art'], de(a['strike'], 0 if a['strike'] == int(a['strike']) else 1),
            datetime.date.fromisoformat(a['verfall']).strftime('%d.%m.%Y'), de(a['praemie_usd'] / 1e6, 1))
    return t + '. Basis: ' + o['basis'] + '. Näherung aus Optionsumsatz, Käufer- oder Verkäuferseite unbekannt.'

def schreiben(sym, o):
    with open(AKTIEN, encoding='utf-8') as f:
        d = json.load(f)
    def symbol(e): return (e.get('symbol') or str(e.get('ticker', '')).split(' ')[0]).upper().replace('-', '.')
    ziel = [e for e in d['einschaetzungen'] if symbol(e) == sym]
    if not ziel:
        print('HINWEIS: kein Eintrag für %s in data/aktien.json, nichts geschrieben' % sym); return
    j = ziel[-1].setdefault('james', {})
    j['flows'] = {'richtung': o['richtung'], 'quelle': 'Cboe, verzögert', 'stand': datetime.date.today().strftime('%d.%m.%Y'),
                  'text': text(o)}
    sys.path.insert(0, os.path.dirname(__file__))
    import trend
    with open(AKTIEN, 'w', encoding='utf-8') as f:
        f.write(trend.kompakt(json.dumps(d, ensure_ascii=False, indent=2)) + '\n')
    print('OK: Option Flows in den Eintrag %s geschrieben' % sym)

def main():
    args = [x for x in sys.argv[1:] if not x.startswith('--')]
    if len(args) != 1: sys.exit(__doc__)
    try:
        o = auswerten(args[0])
    except Fehler as e:
        print('FEHLER: %s' % e); sys.exit(1)
    print(json.dumps(o, ensure_ascii=False, indent=2))
    if '--schreibe' in sys.argv:
        verlauf_speichern(o['symbol'], o)
        schreiben(o['symbol'], o)

if __name__ == '__main__':
    main()
