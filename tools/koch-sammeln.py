#!/usr/bin/env python3
"""Börsen-Beitrag von Markus Koch (YouTube) auswerten: Indikatoren mit Pfeil, Stimmungs-Score.

Braucht GEMINI_API_KEY. Optional SEED_VIDEOS (Links oder IDs, durch Leerzeichen getrennt): diese Videos
werden sicher ausgewertet und bestimmen beim ersten Lauf den Kanal. Sonst wird der Kanal-Feed nach neuen
Videos abgesucht. Es wird KEIN Transkript gespeichert, nur die Auswertung in eigenen Worten
(höchstens zwei kurze Zitate mit Quelle). Ergebnis: data/koch.json
"""
import datetime as dt, zoneinfo, json, os, re, sys, time, urllib.request, urllib.error
import xml.etree.ElementTree as ET

KEY = os.environ.get("GEMINI_API_KEY", "").strip()
MODELS = [m for m in [os.environ.get("GEMINI_VIDEO_MODEL", "").strip(), "gemini-3.8-flash", "gemini-3.7-flash", "gemini-flash-latest"] if m]
BASE = "https://generativelanguage.googleapis.com/v1beta"
DB, KANAL = "data/koch.json", "data/koch-kanal.json"
MAX_PRO_LAUF, MAX_ALTER_TAGE = int(os.environ.get("MAX_PRO_LAUF") or 4), int(os.environ.get("MAX_ALTER_TAGE") or 4)
UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36",
      "Accept-Language": "de-DE,de;q=0.9", "Cookie": "CONSENT=YES+1; SOCS=CAI"}
KATEGORIEN = ["Arbeitsmarkt", "Zinsen & Notenbank", "Inflation", "Öl & Rohstoffe", "Anleihen & Renditen", "Konjunktur",
              "Gewinnsaison", "Marktbreite & Sektoren", "Geopolitik", "Politik & Zölle", "Saisonalität & Chart",
              "Stimmung & Volatilität", "Dollar & Währungen", "Sonstiges"]

PROMPT = """Du hörst einen deutschsprachigen Börsen-Beitrag (Marktstimmung, Börsenthemen) von Markus Koch.
Verstehe SEINE Sicht: woran macht er die Stimmung am US-Aktienmarkt fest? Es geht NUR um die aktuelle Marktlage
(Indizes, Konjunktur- und Arbeitsmarktdaten, Zinsen, Inflation, Anleihen, Öl, Dollar, Volatilität, Marktbreite, Sektoren,
Positionierung, Politik, Geopolitik, Saisonalität, Gewinnsaison insgesamt). Einzelne Aktien oder einzelne Unternehmen
(auch Quartalszahlen oder Kursziele einzelner Firmen) kommen NICHT als Indikator vor und fließen nur insoweit in den
Score ein, wie sie ausdrücklich als Signal für den Gesamtmarkt gelten. Gib KEIN Transkript wieder, schreibe nichts
wörtlich ab (höchstens zwei Zitate mit je unter 15 Wörtern). Antworte ausschließlich als JSON mit diesen Feldern:
- ist_boersenbeitrag: true, wenn es ein Börsen-/Marktbeitrag ist, sonst false (dann reichen die übrigen Felder leer)
- thema: ein Satz, worum es in diesem Beitrag geht
- score: ganze Zahl von -100 (sehr negative Marktstimmung des Sprechers) bis +100 (sehr positive), 0 = neutral
- gesamtstimmung: ein bis zwei Sätze in eigenen Worten
- begruendung: zwei Sätze, warum dieser Score
- indikatoren: Liste (3 bis 10) von Objekten {kategorie, name, lage, pfeil, rolle}
    kategorie = genau eine aus: %s
    name = kurzer Name (z.B. "US-Arbeitsmarktbericht", "Ölpreis", "Marktbreite")
    lage = was dort gerade passiert, in wenigen Worten (z.B. "schwächer als erwartet", "fällt")
    pfeil = Wirkung auf die Börse aus SEINER Sicht: "hoch" (stützt), "runter" (belastet), "seitwaerts" (neutral/unklar)
    rolle = ein Satz, warum ihm das wichtig ist
- zitate: Liste mit höchstens zwei kurzen wörtlichen Zitaten
- sicherheit: hoch|mittel|niedrig (wie gut du den Beitrag verstanden hast)""" % ", ".join(KATEGORIEN)


def get(url, binary=False):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=60) as r:
        b = r.read()
    return b if binary else b.decode("utf-8", "replace")


def vid_id(s):
    m = re.search(r"(?:youtu\.be/|/live/|/shorts/|[?&]v=)([A-Za-z0-9_-]{11})", s) or re.fullmatch(r"([A-Za-z0-9_-]{11})", s.strip())
    return m.group(1) if m else None


def seite(vid):
    """Titel, Datum (JJJJ-MM-TT) und Kanal-ID aus der Videoseite."""
    h = get(f"https://www.youtube.com/watch?v={vid}")
    t = re.search(r'<meta name="title" content="([^"]*)"', h)
    d = (re.search(r'itemprop="datePublished" content="(\d{4}-\d\d-\d\d)', h) or re.search(r'itemprop="uploadDate" content="(\d{4}-\d\d-\d\d)', h)
         or re.search(r'"publishDate":"(\d{4}-\d\d-\d\d)', h) or re.search(r'"startDate":"(\d{4}-\d\d-\d\d)', h))
    c = re.search(r'"channelId":"(UC[\w-]{22})"', h) or re.search(r'itemprop="(?:channelId|identifier)" content="(UC[\w-]{22})"', h)
    import html
    return {"titel": html.unescape(t.group(1)) if t else None, "datum": d.group(1) if d else None, "kanal": c.group(1) if c else None}


def oembed_titel(vid):
    try:
        return json.loads(get("https://www.youtube.com/oembed?format=json&url=https://www.youtube.com/watch?v=" + vid)).get("title")
    except Exception:  # noqa: BLE001
        return None


def feed(kanal):
    x = ET.fromstring(get(f"https://www.youtube.com/feeds/videos.xml?channel_id={kanal}", True))
    ns = {"a": "http://www.w3.org/2005/Atom", "y": "http://www.youtube.com/xml/schemas/2015"}
    out = []
    for e in x.findall("a:entry", ns):
        out.append({"id": e.find("y:videoId", ns).text, "titel": e.find("a:title", ns).text, "datum": e.find("a:published", ns).text[:10], "zeit": e.find("a:published", ns).text})
    return out


def gemini(vid):
    body = {"contents": [{"parts": [{"file_data": {"file_uri": f"https://www.youtube.com/watch?v={vid}"}}, {"text": PROMPT}]}],
            "generationConfig": {"responseMimeType": "application/json", "temperature": 0.2}}
    errors = []
    for m in MODELS:
        for attempt in range(2):
            req = urllib.request.Request(f"{BASE}/models/{m}:generateContent", data=json.dumps(body).encode(), method="POST",
                                         headers={"x-goog-api-key": KEY, "Content-Type": "application/json"})
            try:
                with urllib.request.urlopen(req, timeout=900) as r:
                    res = json.load(r)
                txt = res["candidates"][0]["content"]["parts"][0]["text"].strip()
                txt = re.sub(r"^```(?:json)?|```$", "", txt).strip()
                return json.loads(txt), m, res.get("usageMetadata", {}).get("totalTokenCount")
            except urllib.error.HTTPError as e:
                msg = f"{m}: HTTP {e.code} {e.read().decode(errors='replace')[:300]}"
                errors.append(msg); print(msg)
                if e.code in (429, 500, 503) and attempt == 0:
                    time.sleep(20); continue
                break
            except Exception as e:  # noqa: BLE001
                msg = f"{m}: {e}"; errors.append(msg); print(msg); break
    raise RuntimeError(errors[-1] if errors else "keine Antwort")


def art_von(v):
    """opening = vor dem US-Handelsstart (Berliner Zeit bis 19 Uhr), closing = danach; Titel hat Vorrang."""
    t = (v.get("titel") or "").lower()
    if "closing" in t: return "closing"
    if "opening" in t: return "opening"
    z = v.get("zeit")
    if not z: return None
    h = dt.datetime.fromisoformat(z.replace("Z", "+00:00")).astimezone(zoneinfo.ZoneInfo("Europe/Berlin")).hour
    return "opening" if h < 19 else "closing"


def aufbereiten(d, v, modell, tokens):
    s = max(-100, min(100, int(d.get("score") or 0)))
    pf = "hoch" if s >= 15 else "runter" if s <= -15 else "seitwaerts"
    ind = []
    for i in (d.get("indikatoren") or [])[:10]:
        k = i.get("kategorie") if i.get("kategorie") in KATEGORIEN else "Sonstiges"
        if i.get("kategorie") in ("Einzelwerte", "Unternehmenszahlen"):
            continue  # alte Kategorien: Einzelaktien sind nicht gewünscht
        p = i.get("pfeil") if i.get("pfeil") in ("hoch", "runter", "seitwaerts") else "seitwaerts"
        ind.append({"kategorie": k, "name": str(i.get("name", ""))[:60], "lage": str(i.get("lage", ""))[:80], "pfeil": p, "rolle": str(i.get("rolle", ""))[:240]})
    return {"id": v["id"], "titel": v.get("titel"), "datum": v["datum"], "zeit": v.get("zeit"), "art": art_von(v), "score": s, "pfeil": pf, "thema": d.get("thema"),
            "gesamtstimmung": d.get("gesamtstimmung"), "begruendung": d.get("begruendung"), "indikatoren": ind,
            "zitate": [str(z)[:140] for z in (d.get("zitate") or [])[:2]], "sicherheit": d.get("sicherheit"), "modell": modell, "tokens": tokens}


def speichern(db):
    grenze = str(dt.date.today() - dt.timedelta(days=90))  # Auswertungen älter als 90 Tage fallen heraus
    db["beitraege"] = [b for b in db["beitraege"] if b["datum"] >= grenze]
    db["gesehen"] = db["gesehen"][-300:]
    db["beitraege"].sort(key=lambda b: (b["datum"], b.get("zeit") or "", b["id"]), reverse=True)
    db["quelle"] = "Markus Koch (YouTube). Eigene Auswertung der Stimmung, kein Transkript, keine Anlageberatung."
    db["kategorien"] = KATEGORIEN
    try:
        alt = json.load(open(DB, encoding="utf-8"))
        if {k: v for k, v in alt.items() if k != "stand"} == {k: v for k, v in db.items() if k != "stand"}:
            return  # nichts geändert, keine neue Datei
    except Exception:  # noqa: BLE001
        pass
    db["stand"] = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%MZ")
    db["quelle"] = "Markus Koch (YouTube). Eigene Auswertung der Stimmung, kein Transkript, keine Anlageberatung."
    db["kategorien"] = KATEGORIEN
    json.dump(db, open(DB, "w", encoding="utf-8"), ensure_ascii=False, indent=1)



def main():
    if not KEY:
        sys.exit("GEMINI_API_KEY fehlt")
    db = json.load(open(DB, encoding="utf-8")) if os.path.exists(DB) else {"beitraege": [], "gesehen": []}
    db.setdefault("gesehen", [])
    kn = json.load(open(KANAL, encoding="utf-8")) if os.path.exists(KANAL) else {}
    seeds = [x for x in (vid_id(s) for s in os.environ.get("SEED_VIDEOS", "").split()) if x]
    heute = dt.date.today()

    todo = []  # (video, erzwungen)
    for sid in seeds:
        if sid in db["gesehen"] and not os.environ.get("NEU"):
            print("Schon ausgewertet:", sid); continue
        try:
            sp = seite(sid)
        except Exception as e:  # noqa: BLE001
            print("Videoseite nicht lesbar:", sid, e); sp = {"titel": None, "datum": None, "kanal": None}
        if sp["kanal"] and not kn.get("kanal"):
            kn = {"kanal": sp["kanal"], "von_video": sid}
            json.dump(kn, open(KANAL, "w", encoding="utf-8"), indent=1); print("Kanal gefunden:", sp["kanal"])
        if not sp["titel"]:
            sp["titel"] = oembed_titel(sid)
        print("Seed", sid, "Titel:", sp["titel"], "Datum:", sp["datum"])
        todo.append(({"id": sid, "titel": sp["titel"], "datum": sp["datum"] or str(heute)}, True))
    if kn.get("kanal"):
        try:
            fd = feed(kn["kanal"])
            print("Feed:", len(fd), "Videos")
            for e in fd[:8]:
                print("  ", e["id"], e["datum"], e["titel"][:70])
            fmap = {e["id"]: e for e in fd}
            for b in db["beitraege"]:  # Titel/Datum nachbessern, falls beim ersten Mal unbekannt
                if b["id"] in fmap:
                    b["titel"], b["datum"], b["zeit"] = fmap[b["id"]]["titel"], fmap[b["id"]]["datum"], fmap[b["id"]]["zeit"]
                    b["art"] = art_von(b)
            for t, _ in todo:
                if t["id"] in fmap:
                    t["titel"], t["datum"], t["zeit"] = fmap[t["id"]]["titel"], fmap[t["id"]]["datum"], fmap[t["id"]]["zeit"]
            neu = [e for e in fd if e["id"] not in db["gesehen"] and e["id"] not in [t[0]["id"] for t in todo]
                   and (heute - dt.date.fromisoformat(e["datum"])).days <= MAX_ALTER_TAGE]
            for e in sorted(neu, key=lambda e: e["datum"])[-MAX_PRO_LAUF:]:
                todo.append((e, False))
        except Exception as e:  # noqa: BLE001
            print("Feed nicht lesbar:", e)
    else:
        print("Kanal unbekannt (SEED_VIDEOS mit einem Video des Kanals angeben)")
    if not todo:
        print("Nichts Neues."); speichern(db); return

    for v, _ in todo:
        print("Werte aus:", v["id"], v.get("titel"), v["datum"], art_von(v))
        try:
            d, m, tok = gemini(v["id"])
        except Exception as e:  # noqa: BLE001
            print("  nicht ausgewertet (neuer Versuch beim nächsten Lauf):", str(e)[:200]); continue
        db["gesehen"].append(v["id"])
        if not d.get("ist_boersenbeitrag", True):
            print("  kein Börsenbeitrag, übersprungen"); continue
        db["beitraege"] = [b for b in db["beitraege"] if b["id"] != v["id"]]
        db["beitraege"].append(aufbereiten(d, v, m, tok))
        print(f"  Score {db['beitraege'][-1]['score']} Pfeil {db['beitraege'][-1]['pfeil']} ({tok} Tokens)")
    speichern(db)

main()
