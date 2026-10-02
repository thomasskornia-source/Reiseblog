#!/usr/bin/env python3
"""Option Flows (Näherung) für James im Aktien-Check.

Aufruf:  python3 tools/optionsfluesse.py KO        (nur US-Aktien mit börsengehandelten Optionen)
Quelle: öffentliche, verzögerte Optionsdaten der Cboe (cdn.cboe.com, kostenlos, inoffizielle Schnittstelle):
alle Kontrakte mit Tagesvolumen, offenen Positionen (Open Interest), Geld-/Briefkurs und letztem Preis.
Richtung: put_call_relativ = heutiges Put/Call-Volumen geteilt durch das Put/Call-Verhältnis der offenen Positionen;
bis 0,65 bullisch (heute ungewöhnlich call-lastig), ab 1,4 bärisch, dazwischen neutral.
Ausgabe: JSON. Fehler (kein US-Ticker, keine Optionen, nicht abrufbar): Exit-Code 1, Zeile "FEHLER: …" – dann
keine Option Flows angeben („keine Daten“), nichts schätzen.

WICHTIG, ehrlich einordnen: Das ist KEIN echter Institutionen-Flow. Die Daten zeigen, WO heute Umsatz war
(Calls oder Puts, Prämie, ungewöhnlich hohes Volumen gegenüber den offenen Positionen), aber nicht, ob gekauft oder
verkauft wurde und von wem. Bezahlanbieter (z. B. Unusual Whales, FlowAlgo) liefern Käufer-/Verkäuferseite, Sweeps
und Blocks; das fehlt hier.
"""
import datetime, json, re, sys, urllib.request

def holen(sym):
    url = 'https://cdn.cboe.com/api/global/delayed_quotes/options/%s.json' % sym
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)

def main():
    if len(sys.argv) != 2: sys.exit(__doc__)
    sym = sys.argv[1].strip().upper()
    if not re.fullmatch(r'[A-Z]{1,5}', sym):
        print('FEHLER: %s ist kein US-Ticker (nur US-Aktien haben hier Optionsdaten)' % sym); sys.exit(1)
    try:
        j = holen(sym)
    except Exception as e:
        print('FEHLER: keine Optionsdaten für %s (%s)' % (sym, e)); sys.exit(1)
    d = j.get('data', {}); opts = d.get('options') or []
    heute = datetime.date.today()
    kurs = d.get('current_price')
    zeilen = []
    for o in opts:
        m = re.fullmatch(r'([A-Z]+)(\d{6})([CP])(\d{8})', o.get('option', ''))
        if not m or m.group(1) != sym: continue
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
        print('FEHLER: keine Optionskontrakte für %s gefunden' % sym); sys.exit(1)
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
    # Calls haben immer mehr Umsatz und Prämie als Puts (Stillhalter, höhere Preise). Darum wird das heutige
    # Put/Call-Volumen mit dem Put/Call-Verhältnis der offenen Positionen (Normalwert dieser Aktie) verglichen.
    rel = (pv / cv) / (poi / coi) if cv and coi and poi else None
    if gesamt_p < 500000 or (cv + pv) < 1000 or rel is None: richtung, stark = 'neutral', 'gering (wenig Umsatz)'
    elif rel <= 0.65: richtung, stark = 'bullisch', 'mittel'
    elif rel >= 1.4: richtung, stark = 'bärisch', 'mittel'
    else: richtung, stark = 'neutral', 'mittel'
    out = {
        'symbol': sym, 'quelle': 'Cboe verzögerte Optionsdaten', 'stand': j.get('timestamp'),
        'richtung': richtung, 'aussagekraft': stark,
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
    print(json.dumps(out, ensure_ascii=False, indent=2))

main()
