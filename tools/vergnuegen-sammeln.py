#!/usr/bin/env python3
"""Sammelt Tipps für die Seite „Vergnügen“ aus den Quellen in data/vergnuegen-quellen.json.

Je Quelle wird die Seite geladen, der sichtbare Text an Gemini gegeben und daraus eine Liste von Tipps (Fakten, eigene Kurzfassung,
kein abgeschriebener Text) gewonnen. Orte werden mit OpenStreetMap (Nominatim) in Koordinaten umgerechnet, damit die Karte sie zeigt.
Ergebnis: data/vergnuegen.json. Quellen mit status „entfernt“ oder abruf=false werden übersprungen. Braucht GEMINI_API_KEY.
Aufbewahrung: Termine verschwinden 2 Tage nach Ende, Tipps ohne Datum nach 120 Tagen ohne neue Nennung.
"""
import datetime as dt, hashlib, html, json, os, re, sys, time, urllib.parse, urllib.request, urllib.error

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D = lambda n: os.path.join(ROOT, "data", n)
KEY = os.environ.get("GEMINI_API_KEY", "").strip()
MODELS = ["gemini-3.8-flash", "gemini-flash-latest"]
BASE = "https://generativelanguage.googleapis.com/v1beta"
UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36", "Accept-Language": "de-DE,de;q=0.9"}
TAGS = {
    "events": ["Musik", "Familie", "Draußen", "Kultur", "Märkte", "Kostenlos", "Abends"],
    "food": ["Bayerisch", "Italienisch", "Asiatisch", "Brunch", "Biergarten", "Vegetarisch", "Café", "Mit Hund"],
    "unterwegs": ["Sehenswert", "Viertel", "Grün", "Museen", "Shopping", "Mode", "Mit Hund"],
    "ausflug": ["Berge", "See", "Wandern", "Bahn", "Mit Hund", "Pferde", "Schlösser"],
    "kino": ["Kino", "Open Air", "Komödie", "Krimi", "Doku", "Mediathek", "Stream"],
}
HEUTE = dt.date.today()
MAX_ZEICHEN, MAX_PRO_QUELLE, MAX_PRO_RUBRIK = 24000, 10, 80
MAX_QUELLEN_PRO_LAUF, PAUSE = 8, 12   # schont das gemeinsame kostenlose Gemini-Kontingent (auch Börsenstimmung und Rätsel nutzen es)


def get(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=45) as r:
        return r.read().decode("utf-8", "replace")


def text_von(h):
    h = re.sub(r"(?is)<(script|style|noscript|svg|nav|footer|header)\b.*?</\1>", " ", h)
    h = re.sub(r"(?s)<!--.*?-->", " ", h)
    h = re.sub(r"(?i)</(p|div|li|h\d|tr|br|section|article)>", "\n", h)
    t = html.unescape(re.sub(r"<[^>]+>", " ", h))
    t = re.sub(r"[ \t\r\f\v]+", " ", t)
    return re.sub(r"\n\s*\n+", "\n", t).strip()[:MAX_ZEICHEN]


def prompt(q):
    return f"""Heute ist der {HEUTE.isoformat()}. Unten steht der Text einer Webseite ({q['name']}, Rubrik "{q['rubrik']}") für Münchner Freizeittipps.
Entnimm bis zu {MAX_PRO_QUELLE} konkrete, besuchbare Tipps (Veranstaltung, Lokal, Ort, Ausflugsziel, Film/Kinotermin) in München oder im Umland.
Nur Fakten aus dem Text, nichts erfinden. Schreibe NICHT ab: "kurz" ist eine eigene Kurzfassung in höchstens 25 Wörtern.
Veranstaltungen, die vor heute zu Ende sind, lässt du weg. Antworte ausschließlich als JSON-Liste von Objekten mit den Feldern:
titel (kurz), ort (Name des Orts/Lokals), adresse (Straße Nr, PLZ München, wenn genannt, sonst ""), datum (JJJJ-MM-TT oder ""), datum_bis (JJJJ-MM-TT oder ""),
zeit ("19:30" oder ""), preis (z.B. "frei", "ab 12 €", sonst ""), dauer (sonst ""), kurz, tags (Liste, NUR aus: {", ".join(TAGS[q['rubrik']])}).
Wenn die Seite keine passenden Tipps enthält, antworte mit [].

TEXT:
"""


def gemini(p):
    body = {"contents": [{"parts": [{"text": p}]}], "generationConfig": {"responseMimeType": "application/json", "temperature": 0.2}}
    fehler = ""
    for m in MODELS:
        for versuch in range(1):
            req = urllib.request.Request(f"{BASE}/models/{m}:generateContent", data=json.dumps(body).encode(), method="POST",
                                         headers={"x-goog-api-key": KEY, "Content-Type": "application/json"})
            try:
                with urllib.request.urlopen(req, timeout=75) as r:
                    t = json.load(r)["candidates"][0]["content"]["parts"][0]["text"].strip()
                return json.loads(re.sub(r"^```(?:json)?|```$", "", t).strip())
            except urllib.error.HTTPError as e:
                fehler = f"{m}: HTTP {e.code}"
                print(fehler, flush=True)
                break
            except Exception as e:  # noqa: BLE001
                fehler = f"{m}: {e}"; print(fehler, flush=True); break
    raise RuntimeError(fehler)


GEO = {}
try:
    GEO = json.load(open(D("vergnuegen-geo.json"), encoding="utf-8"))
except Exception:  # noqa: BLE001
    pass


def geo(ort, adresse):
    for suche in [s for s in [", ".join(x for x in (ort, adresse) if x), ort] if s]:
        k = suche.lower()
        if k in GEO:
            if GEO[k]:
                return GEO[k]
            continue
        q = suche if re.search(r"münchen|munich|bayern|\d{5}", suche, re.I) else suche + ", München"
        time.sleep(1.2)  # Nominatim: höchstens eine Anfrage pro Sekunde
        try:
            u = "https://nominatim.openstreetmap.org/search?format=json&limit=1&countrycodes=de&q=" + urllib.parse.quote(q)
            r = json.loads(get_geo(u))
            GEO[k] = [round(float(r[0]["lat"]), 5), round(float(r[0]["lon"]), 5)] if r else None
        except Exception:  # noqa: BLE001
            GEO[k] = None
        if GEO[k]:
            return GEO[k]
    return None


def get_geo(u):
    req = urllib.request.Request(u, headers={"User-Agent": "Reiseblog-Vergnuegen/1.0 (private Seite, taeglich wenige Abfragen)"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8")


def datum_ok(s):
    return bool(re.fullmatch(r"\d{4}-\d\d-\d\d", s or ""))


def main():
    if not KEY:
        print("GEMINI_API_KEY fehlt."); return 0
    quellen = json.load(open(D("vergnuegen-quellen.json"), encoding="utf-8"))
    try:
        alt = json.load(open(D("vergnuegen.json"), encoding="utf-8"))
    except Exception:  # noqa: BLE001
        alt = []
    db = {x["id"]: x for x in alt}
    ok = fehler = neu = 0
    start = time.time()
    try:
        lauf = json.load(open(D("vergnuegen-lauf.json"), encoding="utf-8"))
    except Exception:  # noqa: BLE001
        lauf = {}
    quellen = [q for q in quellen if q.get("status") != "entfernt" and q.get("abruf", True)]
    quellen.sort(key=lambda q: lauf.get(q["id"], ""))   # am längsten nicht abgerufene zuerst
    hintereinander = 0
    for q in quellen[:MAX_QUELLEN_PRO_LAUF]:
        if ok or fehler:
            time.sleep(PAUSE)
        if hintereinander >= 2:
            print("Zwei Mal in Folge Tempolimit, Abbruch bis zum nächsten Lauf"); break
        if time.time() - start > 1500:
            print("Zeitbudget erreicht, Rest beim nächsten Lauf"); break
        if q.get("status") == "entfernt" or not q.get("abruf", True):
            continue
        try:
            items = gemini(prompt(q) + text_von(get(q["url"])))
            if not isinstance(items, list):
                raise RuntimeError("keine Liste")
        except Exception as e:  # noqa: BLE001
            fehler += 1; hintereinander += 1; print("FEHLER", q["id"], str(e)[:200], flush=True); continue
        ok += 1; hintereinander = 0; lauf[q["id"]] = HEUTE.isoformat()
        for it in items[:MAX_PRO_QUELLE]:
            if not isinstance(it, dict) or not it.get("titel"):
                continue
            d1, d2 = (it.get("datum") if datum_ok(it.get("datum")) else ""), (it.get("datum_bis") if datum_ok(it.get("datum_bis")) else "")
            if (d2 or d1) and (d2 or d1) < HEUTE.isoformat():
                continue
            iid = q["rubrik"] + "-" + hashlib.sha1((it["titel"].strip().lower() + d1).encode()).hexdigest()[:10]
            x = db.get(iid) or {"id": iid}
            if "lat" not in x:
                g = geo(it.get("ort", ""), it.get("adresse", ""))
                if g:
                    x["lat"], x["lon"] = g
            x.update({"rubrik": q["rubrik"], "titel": it["titel"].strip()[:120], "ort": (it.get("ort") or "")[:80], "adresse": (it.get("adresse") or "")[:100],
                      "datum": d1, "datum_bis": d2, "zeit": (it.get("zeit") or "")[:20], "preis": (it.get("preis") or "")[:30], "dauer": (it.get("dauer") or "")[:30],
                      "kurz": (it.get("kurz") or "")[:200], "tags": [t for t in (it.get("tags") or []) if t in TAGS[q["rubrik"]]],
                      "quelle": q["name"], "url": q["url"], "stand": HEUTE.isoformat()})
            if iid not in db:
                neu += 1
            db[iid] = x
        print("ok", q["id"], len(items), "Tipps", flush=True)
    grenze = (HEUTE - dt.timedelta(days=2)).isoformat(); alt_grenze = (HEUTE - dt.timedelta(days=120)).isoformat()
    out = []
    for x in db.values():
        ende = x.get("datum_bis") or x.get("datum")
        if ende and ende < grenze:
            continue
        if not ende and x.get("stand", "") < alt_grenze:
            continue
        out.append(x)
    out.sort(key=lambda x: (x["rubrik"], x.get("datum") or "9999", x["titel"]))
    je = {}
    final = []
    for x in out:
        je[x["rubrik"]] = je.get(x["rubrik"], 0) + 1
        if je[x["rubrik"]] <= MAX_PRO_RUBRIK:
            final.append(x)
    json.dump(final, open(D("vergnuegen.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    json.dump(lauf, open(D("vergnuegen-lauf.json"), "w", encoding="utf-8"), indent=0)
    json.dump(GEO, open(D("vergnuegen-geo.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=0)
    print(f"Fertig: {ok} Quellen ok, {fehler} Fehler, {neu} neue Tipps, {len(final)} gesamt")
    return 1 if ok == 0 and fehler else 0


sys.exit(main())
