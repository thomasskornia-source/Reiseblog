#!/usr/bin/env python3
"""KI-These mit Quellen je Aktie (Thomas, 15.10.2026, kleiner Test) -> data/thesen.json.

Aufruf:  python3 tools/these-sammeln.py            nimmt die ersten N Aktien der Top 10 (N = Umgebungsvariable ANZAHL, Standard 2)
         ANZAHL=1 TICKER=AMZN python3 tools/these-sammeln.py   eine bestimmte Aktie
Gemini sucht mit der Google-Suche (Werkzeug google_search) nach Termin (Quartalszahlen), Kursziele/Analysten, Branchenthema, Kapitalausgaben/Zahlen und aktuellen Meldungen.
Eingabe: Kurs, James-Score und, wenn vorhanden, der Optionsfluss aus data/sektorflow.json (Score, größte Kontrakte). Ausgabe: Überschrift, Zusammenfassung,
Katalysatoren mit Beleg (Quelle + Datum), Risiken, Flow-Bezug und die Quellenliste aus der Suche. Keine Kauf- oder Verkaufsempfehlung, keine Handelsideen.
Jeder Lauf zählt seine Anfragen im Log (Kontingent!). Braucht GEMINI_API_KEY. Je Aktie wird nur einmal pro Tag erzeugt, alte Thesen älter als 14 Tage fallen weg.
"""
import datetime as dt, json, os, re, sys, time, urllib.request, urllib.error

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D = lambda n: os.path.join(ROOT, "data", n)
KEY = os.environ.get("GEMINI_API_KEY", "").strip()
MODELS = ["gemini-3.8-flash", "gemini-flash-latest"]
BASE = "https://generativelanguage.googleapis.com/v1beta"
HEUTE = dt.date.today().isoformat()
ANFRAGEN = 0


def gemini(p):
    """Eine Anfrage mit Suche; gibt (Text, Quellen[{titel,url}]) zurück."""
    global ANFRAGEN
    body = {"contents": [{"parts": [{"text": p}]}], "tools": [{"google_search": {}}], "generationConfig": {"temperature": 0.2}}
    fehler = ""
    for m in MODELS:
        for versuch in range(3):
            req = urllib.request.Request(f"{BASE}/models/{m}:generateContent", data=json.dumps(body).encode(), method="POST",
                                         headers={"x-goog-api-key": KEY, "Content-Type": "application/json"})
            ANFRAGEN += 1
            try:
                with urllib.request.urlopen(req, timeout=180) as r:
                    j = json.load(r)
                c = j["candidates"][0]
                t = "".join(x.get("text", "") for x in c["content"]["parts"]).strip()
                qs, seen = [], set()
                for g in (c.get("groundingMetadata") or {}).get("groundingChunks", []):
                    w = g.get("web") or {}
                    if w.get("uri") and w["uri"] not in seen:
                        seen.add(w["uri"]); qs.append({"titel": w.get("title") or "", "url": w["uri"]})
                print(f"Anfrage ok ({m}), {len(qs)} Quellen", flush=True)
                return t, qs
            except urllib.error.HTTPError as e:
                fehler = f"{m}: HTTP {e.code}"; print(fehler, flush=True)
                if e.code in (429, 500, 502, 503, 504) and versuch < 2:
                    time.sleep(60 * (versuch + 1)); continue
                break
            except Exception as e:  # noqa: BLE001
                fehler = f"{m}: {e}"; print(fehler, flush=True); break
    raise RuntimeError(fehler)


def flow_text(t):
    try:
        sf = json.load(open(D("sektorflow.json"), encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return "Optionsfluss: keine Daten vorhanden."
    tage = sorted(sf["tage"])[-14:]
    bull = bear = 0
    for d in tage:
        v = sf["tage"][d].get(t)
        if v: bull += v[0] + v[1]; bear += v[2]
    z = f"Optionsfluss der letzten {len(tage)} Handelstage (geschätzte Seite): bullisch {bull}, bärisch {bear}, Score {bull - bear:+d}."
    g = (sf.get("gross") or {}).get(t) or []
    for c in g:
        z += f" Großer Kontrakt am {sf['stand']}: {'Call' if c[0] == 'C' else 'Put'} Strike {c[1]} Verfall {c[2]}, {c[3]} Kontrakte, Prämie {c[4]} Tsd. $, Seite {c[5] or 'unklar'}."
    return z


def erzeugen(x):
    t = x["ticker"]
    p = (f"Heute ist {HEUTE}. Recherchiere mit der Websuche aktuelle Informationen zur Aktie {t} ({x['name']}, Sektor {x.get('sektor', '')}) und schreibe eine kurze 'These': "
         "Welche Ereignisse treiben den Kurs und den Optionsfluss? Suche gezielt nach (1) Termin der nächsten Quartalszahlen und Erwartungen, (2) Kurszielen und Analystenmeinungen der letzten Wochen, "
         "(3) dem wichtigsten Branchenthema, (4) Investitionen, Cashflow oder Prognose des Unternehmens, (5) aktuellen Meldungen der letzten 7 Tage. "
         f"Gegeben: Kurs {x.get('kurs')} $, James-Score {x.get('punkte')} von 11, Lage: {x.get('lage')}. {flow_text(t)} "
         "Antworte NUR mit einem JSON-Objekt (ohne Markdown) in deutscher Sprache mit den Feldern: "
         "titel (Überschrift, max. 90 Zeichen), zusammenfassung (3 bis 5 Sätze), "
         "katalysatoren (Liste mit 3 bis 5 Objekten: art = earnings|sektor|guidance|technik|nachricht, titel, text (2 bis 3 Sätze, eigene Worte), beleg (Quelle und Datum, z. B. 'Reuters, 12.10.2026', mit kurzem Zitat von höchstens 15 Wörtern)), "
         "flow_bezug (1 bis 2 Sätze: passt der Optionsfluss zur These oder läuft er dagegen?), risiken (Liste mit 3 bis 5 kurzen Sätzen). "
         "Regeln: Nur belegte Fakten, nichts erfinden; wenn du etwas nicht findest, lass es weg. Keine Kauf- oder Verkaufsempfehlung, keine Optionsstrategien, keine Kursprognose als Gewissheit. "
         "Texte Dritter nicht abschreiben, nur eigene Zusammenfassung.")
    txt, qs = gemini(p)
    m = re.search(r"\{.*\}", txt, re.S)
    if not m: raise RuntimeError("keine JSON-Antwort")
    j = json.loads(m.group(0))
    j.update({"ticker": t, "name": x["name"], "datum": HEUTE, "quellen": qs[:30]})
    return j


def main():
    if not KEY:
        print("GEMINI_API_KEY fehlt."); return 0
    top = json.load(open(D("top10.json"), encoding="utf-8")).get("top10", [])
    n = int(os.environ.get("ANZAHL", "2") or 2); wunsch = os.environ.get("TICKER", "").strip().upper()
    wahl = [x for x in top if x["ticker"] == wunsch] if wunsch else top[:n]
    if wunsch and not wahl:
        beo = json.load(open(D("beobachtung.json"), encoding="utf-8")) if os.path.exists(D("beobachtung.json")) else {}
        wahl = [x for x in (beo.get("beobachtung") or beo.get("aktien") or []) if x.get("ticker") == wunsch]
    try: alt = json.load(open(D("thesen.json"), encoding="utf-8"))
    except Exception:  # noqa: BLE001
        alt = {"thesen": {}}
    th = alt.get("thesen", {})
    for x in wahl:
        if th.get(x["ticker"], {}).get("datum") == HEUTE and not wunsch:
            print(x["ticker"], "heute schon erzeugt"); continue
        try:
            th[x["ticker"]] = erzeugen(x); print(x["ticker"], "These erzeugt", flush=True)
        except Exception as e:  # noqa: BLE001
            print(x["ticker"], "fehlgeschlagen:", str(e)[:200], flush=True)
    grenze = (dt.date.today() - dt.timedelta(days=14)).isoformat()
    th = {k: v for k, v in th.items() if v.get("datum", "") >= grenze}
    with open(D("thesen.json"), "w", encoding="utf-8") as fh:
        json.dump({"stand": HEUTE, "thesen": th}, fh, ensure_ascii=False, indent=1)
    print(f"Gemini-Anfragen in diesem Lauf: {ANFRAGEN}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
