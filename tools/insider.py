#!/usr/bin/env python3
"""Insiderkäufe und Datum der letzten Zahlen aus den SEC-Meldungen (für die Top 10 im Aktien-Check, kostenlos, ohne KI).

Quelle: SEC EDGAR, Einreichungsliste je Firma (data.sec.gov/submissions) und die Form-4-Meldungen der letzten 90 Tage
(Käufe und Verkäufe von Vorständen, Direktoren und Großaktionären). Gezählt werden nur Transaktionscode P (Kauf am offenen Markt)
und S (Verkauf); Optionsausübungen, Schenkungen und Steuereinbehalt zählen nicht. Verkäufe sind oft planmäßig und daher schwach.
Zahlen: Datum der letzten Einreichung 10-Q oder 10-K (nicht das Datum der Bekanntgabe, das liegt meist 0 bis 2 Tage davor).

Aufruf aus tools/screener.py:  insider.holen(cik, kontakt) -> {'insider': {...}, 'zahlen': {...}}   (kontakt = SEC_KONTAKT)
"""
import datetime, json, time, urllib.request
import xml.etree.ElementTree as ET

SUB = 'https://data.sec.gov/submissions/CIK%010d.json'
ARCH = 'https://www.sec.gov/Archives/edgar/data/%d/%s/%s'
MAX_FORM4 = 60

def _web(url, ua):
    req = urllib.request.Request(url, headers={'User-Agent': ua})
    with urllib.request.urlopen(req, timeout=40) as r:
        data = r.read()
    time.sleep(0.15)   # unter der SEC-Grenze von 10 Abrufen pro Sekunde
    return data

def _text(el, pfad):
    x = el.find(pfad) if el is not None else None
    return x.text.strip() if x is not None and x.text else None

def _form4(xml_bytes):
    """Liefert [(code, aktien, preis, personen_id)] aus einer Form-4-Datei."""
    out = []
    root = ET.fromstring(xml_bytes)
    owner = _text(root, 'reportingOwner/reportingOwnerId/rptOwnerCik') or '?'
    for t in root.findall('nonDerivativeTable/nonDerivativeTransaction'):
        code = _text(t, 'transactionCoding/transactionCode')
        try:
            n = float(_text(t, 'transactionAmounts/transactionShares/value') or 0)
            p = float(_text(t, 'transactionAmounts/transactionPricePerShare/value') or 0)
        except ValueError:
            continue
        out.append((code, n, p, owner))
    return out

def holen(cik, kontakt, tage=90):
    ua = 'Reiseblog-Screener %s' % kontakt
    sub = json.loads(_web(SUB % cik, ua))
    rec = sub['filings']['recent']
    heute = datetime.date.today()
    zahlen = None
    for form, datum in zip(rec['form'], rec['filingDate']):
        if form in ('10-Q', '10-K'):
            d = datetime.date.fromisoformat(datum)
            zahlen = {'form': form, 'datum': d.strftime('%d.%m.%Y'), 'tage': (heute - d).days}
            break
    kaeufe = verkaeufe = 0; summe = 0.0; personen = set(); zaehler = 0; letzter = None
    for form, datum, acc, doc in zip(rec['form'], rec['filingDate'], rec['accessionNumber'], rec['primaryDocument']):
        if form != '4': continue
        d = datetime.date.fromisoformat(datum)
        if (heute - d).days > tage: break
        zaehler += 1
        if zaehler > MAX_FORM4: break
        try:
            tr = _form4(_web(ARCH % (cik, acc.replace('-', ''), doc.split('/')[-1]), ua))
        except Exception:
            continue
        for code, n, p, person in tr:
            if code == 'P' and n > 0:
                kaeufe += 1; summe += n * p; personen.add(person)
                letzter = max(letzter, d) if letzter else d
            elif code == 'S' and n > 0:
                verkaeufe += 1
    return {'insider': {'kaeufe': kaeufe, 'kaeufer': len(personen), 'summe_usd': int(summe), 'verkaeufe': verkaeufe, 'tage': tage,
                        'letzter_kauf': letzter.strftime('%d.%m.%Y') if letzter else None, 'meldungen': min(zaehler, MAX_FORM4)},
            'zahlen': zahlen}
