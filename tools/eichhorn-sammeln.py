#!/usr/bin/env python3
"""Eichhorn Coaching (YouTube-Podcast) auswerten: Stillhalter-Regeln, Indikatoren und Informationsquellen je Folge.

Braucht GEMINI_API_KEY. Optional SEED_VIDEOS (Links oder IDs, durch Leerzeichen getrennt): diese Videos werden sicher
ausgewertet. Optional BACKFILL (Zahl): so viele der neuesten, noch nicht gesehenen Videos des Feeds nachholen.
Es wird KEIN Transkript gespeichert, nur die Auswertung in eigenen Worten (höchstens zwei kurze Zitate mit Quelle).
Ergebnis: data/eichhorn.json
"""
import datetime as dt, json, os, re, sys, time, urllib.request, urllib.error
import xml.etree.ElementTree as ET

KEY = os.environ.get("GEMINI_API_KEY", "").strip()
MODELS = [m for m in [os.environ.get("GEMINI_VIDEO_MODEL", "").strip(), "gemini-3.8-flash", "gemini-3.7-flash", "gemini-flash-latest"] if m]
BASE = "https://generativelanguage.googleapis.com/v1beta"
DB, KANAL = "data/eichhorn.json", "data/eichhorn-kanal.json"
HANDLE = "eichhorncoaching"
MAX_PRO_LAUF, MAX_ALTER_TAGE = int(os.environ.get("MAX_PRO_LAUF") or 3), int(os.environ.get("MAX_ALTER_TAGE") or 10)
BACKFILL = int(os.environ.get("BACKFILL") or 0)
BEHALTEN_TAGE = 365
UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36",
      "Accept-Language": "de-DE,de;q=0.9", "Cookie": "CONSENT=YES+1; SOCS=CAI"}
BEREICHE = ["Strike & Delta", "Laufzeit", "Prämie & Rendite", "Positionsgröße & Risiko", "Absicherung & Spreads",
            "Ausstieg & Gewinnmitnahme", "Rollen & Reparatur", "Volatilität & Marktphase", "Titelauswahl",
            "Wheel & Einstieg", "Steuern & Broker", "Sonstiges"]
ARTEN = ["Kennzahl", "Index", "Datenquelle", "Werkzeug", "Person/Medium"]

PROMPT = """Du hörst eine Folge des deutschsprachigen Eichhorn-Coaching-Podcasts (Optionshandel, Stillhalter-Strategien).
Ziel: die STILLHALTER-REGELN der Sprecher (Alexander Eichhorn, Maximilian Bothe) für eine strukturierte Strategie-Übersicht
zu sammeln, dazu alle genannten Indikatoren und Informationsquellen für die Marktbeobachtung.
Gib KEIN Transkript wieder, schreibe nichts wörtlich ab (höchstens zwei Zitate mit je unter 15 Wörtern). Erfinde nichts:
nur was in der Folge wirklich gesagt wird. Konkrete Zahlen (Delta, Tage, Prozent, Anzahl Positionen) nur, wenn sie genannt werden.
Antworte ausschließlich als JSON mit diesen Feldern:
- ist_stillhalter_inhalt: true, wenn die Folge Optionen/Stillhalter/Markt behandelt, sonst false (dann reichen die übrigen Felder leer)
- thema: ein Satz, worum es in der Folge geht
- marktlage: ein bis zwei Sätze in eigenen Worten, falls die Folge die aktuelle Marktlage einschätzt, sonst leer
- regeln: Liste (0 bis 12) von Objekten {bereich, regel, zahl, begruendung, art}
    bereich = genau eine aus: %s
    regel = die Regel als kurzer Satz in eigenen Worten (z.B. "Positionen spätestens ca. 10 Tage vor Verfall schließen")
    zahl = genannte Kennzahl dazu (z.B. "10 Tage", "50 %%", "Delta 20"), sonst leer
    begruendung = ein Satz, warum die Sprecher das so machen
    art = "regel" (klare Handlungsvorgabe), "gewohnheit" (machen sie meist so) oder "warnung" (was man vermeiden soll)
- indikatoren: Liste (0 bis 12) von Objekten {name, art, wozu, lage}
    name = kurzer Name (z.B. "VIX", "VVIX", "VIX-Terminstruktur", "Implied Volatility Rank", "Put/Call-Ratio")
    art = genau eine aus: %s
    wozu = ein Satz, wofür sie ihn nutzen
    lage = wie sie ihn gerade einschätzen (wenige Worte), sonst leer
- quellen: Liste (0 bis 8) von Objekten {name, wozu}: genannte Websites, Datenanbieter, Broker-Werkzeuge, Bücher, Newsletter
- zitate: Liste mit höchstens zwei kurzen wörtlichen Zitaten
- sicherheit: hoch|mittel|niedrig (wie gut du die Folge verstanden hast)""" % (", ".join(BEREICHE), ", ".join(ARTEN))


def get(url, binary=False):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=60) as r:
        b = r.read()
    return b if binary else b.decode("utf-8", "replace")


def vid_id(s):
    m = re.search(r"(?:youtu\.be/|/live/|/shorts/|[?&]v=)([A-Za-z0-9_-]{11})", s) or re.fullmatch(r"([A-Za-z0-9_-]{11})", s.strip())
    return m.group(1) if m else None


def kanal_id_von_handle():
    h = get(f"https://www.youtube.com/@{HANDLE}")
    m = (re.search(r'"channelId":"(UC[\w-]{22})"', h) or re.search(r'youtube\.com/channel/(UC[\w-]{22})', h)
         or re.search(r'itemprop="(?:channelId|identifier)" content="(UC[\w-]{22})"', h))
    return m.group(1) if m else None


def seite(vid):
    h = get(f"https://www.youtube.com/watch?v={vid}")
    import html
    t = re.search(r'<meta name="title" content="([^"]*)"', h)
    d = (re.search(r'itemprop="datePublished" content="(\d{4}-\d\d-\d\d)', h) or re.search(r'"publishDate":"(\d{4}-\d\d-\d\d)', h)
         or re.search(r'"startDate":"(\d{4}-\d\d-\d\d)', h))
    c = re.search(r'"channelId":"(UC[\w-]{22})"', h)
    return {"titel": html.unescape(t.group(1)) if t else None, "datum": d.group(1) if d else None, "kanal": c.group(1) if c else None}


def feed(kanal):
    x = ET.fromstring(get(f"https://www.youtube.com/feeds/videos.xml?channel_id={kanal}", True))
    ns = {"a": "http://www.w3.org/2005/Atom", "y": "http://www.youtube.com/xml/schemas/2015"}
    return [{"id": e.find("y:videoId", ns).text, "titel": e.find("a:title", ns).text,
             "datum": e.find("a:published", ns).text[:10], "zeit": e.find("a:published", ns).text} for e in x.findall("a:entry", ns)]


def bekannte(db):
    """Bisher genannte Indikatornamen, damit die KI gleiche Dinge gleich benennt."""
    namen = {}
    for b in db.get("beitraege", []):
        for i in b.get("indikatoren", []):
            namen[i["name"]] = namen.get(i["name"], 0) + 1
    if not namen:
        return ""
    z = ["Bisher genannte Indikatoren (Name, Anzahl Folgen). Verwende für dieselbe Sache möglichst genau diesen Namen;",
         "neue, hier noch nicht genannte nimmst du ausdrücklich zusätzlich auf:"]
    z += ["- %s (%d)" % (n, c) for n, c in sorted(namen.items(), key=lambda x: -x[1])[:40]]
    return "\n".join(z)


def gemini(vid, db):
    teile = [{"file_data": {"file_uri": f"https://www.youtube.com/watch?v={vid}"}}, {"text": PROMPT}]
    b = bekannte(db)
    if b:
        teile.append({"text": b})
    gen = {"responseMimeType": "application/json", "temperature": 0.2, "mediaResolution": "MEDIA_RESOLUTION_LOW"}
    errors = []
    for m in MODELS:
        for attempt in range(2):
            body = {"contents": [{"parts": teile}], "generationConfig": gen}
            req = urllib.request.Request(f"{BASE}/models/{m}:generateContent", data=json.dumps(body).encode(), method="POST",
                                         headers={"x-goog-api-key": KEY, "Content-Type": "application/json"})
            try:
                with urllib.request.urlopen(req, timeout=int(os.environ.get('GEMINI_TIMEOUT') or 480)) as r:
                    res = json.load(r)
                txt = res["candidates"][0]["content"]["parts"][0]["text"].strip()
                txt = re.sub(r"^```(?:json)?|```$", "", txt).strip()
                return json.loads(txt), m, res.get("usageMetadata", {}).get("totalTokenCount")
            except urllib.error.HTTPError as e:
                msg = f"{m}: HTTP {e.code} {e.read().decode(errors='replace')[:300]}"
                errors.append(msg); print(msg)
                if e.code == 400 and "mediaResolution" in gen and "media" in msg.lower():
                    gen = {k: v for k, v in gen.items() if k != "mediaResolution"}; continue
                if e.code in (429, 500, 503) and attempt < 1:
                    time.sleep(20); continue
                break
            except Exception as e:  # noqa: BLE001
                msg = f"{m}: {e}"; errors.append(msg); print(msg); break
    raise RuntimeError(errors[-1] if errors else "keine Antwort")


def aufbereiten(d, v, modell, tokens):
    def s(x, n):
        return str(x or "")[:n]
    regeln = []
    for r in (d.get("regeln") or [])[:12]:
        if not r.get("regel"):
            continue
        regeln.append({"bereich": r.get("bereich") if r.get("bereich") in BEREICHE else "Sonstiges", "regel": s(r.get("regel"), 200),
                       "zahl": s(r.get("zahl"), 40), "begruendung": s(r.get("begruendung"), 240),
                       "art": r.get("art") if r.get("art") in ("regel", "gewohnheit", "warnung") else "gewohnheit"})
    ind = []
    for i in (d.get("indikatoren") or [])[:12]:
        if i.get("name"):
            ind.append({"name": s(i.get("name"), 60), "art": i.get("art") if i.get("art") in ARTEN else "Kennzahl",
                        "wozu": s(i.get("wozu"), 200), "lage": s(i.get("lage"), 80)})
    qu = [{"name": s(q.get("name"), 80), "wozu": s(q.get("wozu"), 160)} for q in (d.get("quellen") or [])[:8] if q.get("name")]
    return {"id": v["id"], "titel": v.get("titel"), "datum": v["datum"], "zeit": v.get("zeit"), "thema": s(d.get("thema"), 240),
            "marktlage": s(d.get("marktlage"), 300), "regeln": regeln, "indikatoren": ind, "quellen": qu,
            "zitate": [str(z)[:140] for z in (d.get("zitate") or [])[:2]], "sicherheit": d.get("sicherheit"), "modell": modell, "tokens": tokens}


def speichern(db):
    grenze = str(dt.date.today() - dt.timedelta(days=BEHALTEN_TAGE))  # Auswertungen älter als ein Jahr fallen heraus
    db["beitraege"] = [b for b in db["beitraege"] if b["datum"] >= grenze]
    db["gesehen"] = db["gesehen"][-300:]
    db["beitraege"].sort(key=lambda b: (b["datum"], b.get("zeit") or "", b["id"]), reverse=True)
    db["quelle"] = "Eichhorn Coaching (YouTube-Podcast). Eigene Auswertung in eigenen Worten, kein Transkript, keine Anlageberatung."
    db["bereiche"] = BEREICHE
    try:
        alt = json.load(open(DB, encoding="utf-8"))
        if {k: v for k, v in alt.items() if k != "stand"} == {k: v for k, v in db.items() if k != "stand"}:
            return
    except Exception:  # noqa: BLE001
        pass
    db["stand"] = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%MZ")
    json.dump(db, open(DB, "w", encoding="utf-8"), ensure_ascii=False, indent=1)


def main():
    if not KEY:
        sys.exit("GEMINI_API_KEY fehlt")
    db = json.load(open(DB, encoding="utf-8")) if os.path.exists(DB) else {"beitraege": [], "gesehen": []}
    db.setdefault("gesehen", [])
    kn = json.load(open(KANAL, encoding="utf-8")) if os.path.exists(KANAL) else {}
    seeds = [x for x in (vid_id(s) for s in os.environ.get("SEED_VIDEOS", "").split()) if x]
    heute = dt.date.today()
    if not kn.get("kanal"):
        k = None
        try:
            k = kanal_id_von_handle()
        except Exception as e:  # noqa: BLE001
            print("Kanalseite nicht lesbar:", e)
        if not k and seeds:
            try:
                k = seite(seeds[0])["kanal"]
            except Exception as e:  # noqa: BLE001
                print("Videoseite nicht lesbar:", e)
        if k:
            kn = {"kanal": k, "handle": HANDLE}
            json.dump(kn, open(KANAL, "w", encoding="utf-8"), indent=1); print("Kanal gefunden:", k)

    todo = []
    for sid in seeds:
        if sid in db["gesehen"] and not os.environ.get("NEU"):
            print("Schon ausgewertet:", sid); continue
        try:
            sp = seite(sid)
        except Exception as e:  # noqa: BLE001
            print("Videoseite nicht lesbar:", sid, e); sp = {"titel": None, "datum": None}
        todo.append({"id": sid, "titel": sp["titel"], "datum": sp["datum"] or str(heute)})
    if kn.get("kanal"):
        try:
            fd = feed(kn["kanal"])
            print("Feed:", len(fd), "Videos")
            for e in fd[:8]:
                print("  ", e["id"], e["datum"], e["titel"][:70])
            fmap = {e["id"]: e for e in fd}
            for t in todo:
                if t["id"] in fmap:
                    t.update({k: fmap[t["id"]][k] for k in ("titel", "datum", "zeit")})
            schon = {t["id"] for t in todo}
            neu = [e for e in fd if e["id"] not in db["gesehen"] and e["id"] not in schon
                   and (heute - dt.date.fromisoformat(e["datum"])).days <= MAX_ALTER_TAGE]
            alt = [e for e in fd if e["id"] not in db["gesehen"] and e["id"] not in schon and e not in neu]
            todo += sorted(neu, key=lambda e: e["datum"])[-MAX_PRO_LAUF:]
            if BACKFILL:
                todo += sorted(alt, key=lambda e: e["datum"], reverse=True)[:BACKFILL]
        except Exception as e:  # noqa: BLE001
            print("Feed nicht lesbar:", e)
    else:
        print("Kanal unbekannt (SEED_VIDEOS mit einem Video des Kanals angeben)")
    if not todo:
        print("Nichts Neues."); speichern(db); return

    for v in todo:
        print("Werte aus:", v["id"], v.get("titel"), v["datum"], flush=True)
        try:
            d, m, tok = gemini(v["id"], db)
        except Exception as e:  # noqa: BLE001
            print("  nicht ausgewertet (neuer Versuch beim nächsten Lauf):", str(e)[:200]); continue
        db["gesehen"].append(v["id"])
        if not d.get("ist_stillhalter_inhalt", True):
            print("  kein Optionen-/Marktinhalt, übersprungen"); continue
        db["beitraege"] = [b for b in db["beitraege"] if b["id"] != v["id"]]
        db["beitraege"].append(aufbereiten(d, v, m, tok))
        b = db["beitraege"][-1]
        print(f"  {len(b['regeln'])} Regeln, {len(b['indikatoren'])} Indikatoren ({tok} Tokens)")
    speichern(db)


main()
