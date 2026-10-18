#!/usr/bin/env python3
"""Konzertmodus (Thomas, 18.10.2026): erzeugt zu einer Band das Special -> data/konzerte/<slug>.json, audio/konzert-<slug>.mp3, data/konzerte/index.json.

Aufruf (Umgebungsvariablen): ARTIST (Pflicht), CITY (Pflicht), oder ISSUE_BODY mit den Zeilen "Interpret: ..." und "Stadt: ...".
Gemini sucht mit der Google-Suche und liefert (1) Special-Text, Farben, Wikipedia-Titel, Quellen und (2) acht Lieder mit Herkunft und Bedeutung.
Das Bild kommt nur von Wikipedia/Commons und nur, wenn die Datei frei lizenziert ist (pilicense=free). Danach liest Gemini den Text als MP3 vor.
Anfragen je Lauf: 2 Textanfragen + 1 Sprachanfrage. Braucht GEMINI_API_KEY und ffmpeg. Eingabe wird streng gefiltert (Text kommt aus einem GitHub-Issue).
"""
import base64, datetime as dt, io, json, os, re, subprocess, sys, time, unicodedata, urllib.parse, urllib.request, urllib.error, wave

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D = lambda *p: os.path.join(ROOT, "data", "konzerte", *p)
KEY = os.environ.get("GEMINI_API_KEY", "").strip()
BASE = "https://generativelanguage.googleapis.com/v1beta"
MODELS = ["gemini-3.8-flash", "gemini-flash-latest"]
TTS_ENDPOINT = BASE + "/interactions"
TTS_MODEL = os.environ.get("GEMINI_TTS_MODEL", "gemini-3.8-flash-tts")
VOICE = os.environ.get("GEMINI_TTS_VOICE", "Kore")
HEUTE = dt.date.today().isoformat()
OK_NAME = re.compile(r"^[\w .,&'’+!\-]{1,60}$", re.U)
HEX = re.compile(r"^#[0-9a-fA-F]{6}$")


def slug(s):
    s = unicodedata.normalize("NFD", s.lower().replace("ß", "ss"))
    s = "".join(c for c in s if not unicodedata.combining(c)).replace("&", " and ")
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")[:60]


def eingabe():
    a, c = os.environ.get("ARTIST", "").strip(), os.environ.get("CITY", "").strip()
    body = os.environ.get("ISSUE_BODY", "")
    if not a:
        m = re.search(r"^Interpret:\s*(.+)$", body, re.M)
        a = m.group(1).strip() if m else ""
    if not c:
        m = re.search(r"^Stadt:\s*(.+)$", body, re.M)
        c = m.group(1).strip() if m else ""
    if not OK_NAME.match(a) or not OK_NAME.match(c) or not slug(a):
        raise SystemExit("Eingabe ungültig oder leer (nur Buchstaben, Ziffern und . , & ' + ! -, höchstens 60 Zeichen).")
    return a, c


def gemini(prompt):
    body = {"contents": [{"parts": [{"text": prompt}]}], "tools": [{"google_search": {}}], "generationConfig": {"temperature": 0.3}}
    fehler = ""
    for m in MODELS:
        for versuch in range(3):
            req = urllib.request.Request(f"{BASE}/models/{m}:generateContent", data=json.dumps(body).encode(), method="POST",
                                         headers={"x-goog-api-key": KEY, "Content-Type": "application/json"})
            try:
                with urllib.request.urlopen(req, timeout=240) as r:
                    j = json.load(r)
                c = j["candidates"][0]
                t = "".join(x.get("text", "") for x in c["content"]["parts"]).strip()
                qs, seen = [], set()
                for g in (c.get("groundingMetadata") or {}).get("groundingChunks", []):
                    w = g.get("web") or {}
                    if w.get("uri") and w["uri"] not in seen:
                        seen.add(w["uri"]); qs.append({"titel": (w.get("title") or "")[:120], "url": w["uri"]})
                print(f"Anfrage ok ({m}), {len(qs)} Quellen", flush=True)
                mm = re.search(r"\{.*\}", t, re.S)
                if not mm:
                    raise RuntimeError("keine JSON-Antwort")
                return json.loads(mm.group(0)), qs
            except urllib.error.HTTPError as e:
                fehler = f"{m}: HTTP {e.code}"; print(fehler, flush=True)
                if e.code in (429, 500, 502, 503, 504) and versuch < 2:
                    time.sleep(45 * (versuch + 1)); continue
                break
            except Exception as e:  # noqa: BLE001
                fehler = f"{m}: {e}"; print(fehler, flush=True)
                if versuch < 1:
                    continue
                break
    raise RuntimeError(fehler)


def special(artist, city):
    p = (f"Heute ist {HEUTE}. Thomas geht in {city} auf ein Konzert von {artist}. Recherchiere mit der Websuche über {artist} und schreibe ein Special auf Deutsch. "
         "Antworte NUR mit einem JSON-Objekt (ohne Markdown) mit diesen Feldern: "
         "titel (kurze Überschrift, max. 70 Zeichen), "
         "text (Fließtext aus 4 bis 6 Absätzen, durch Leerzeilen getrennt, insgesamt etwa 450 Wörter: Herkunft und Gründung, Besetzung, Stil, wichtigste Alben und Hits, Bedeutung, Live-Ruf, aktuelle Lage), "
         "sprech (derselbe Text als gesprochene Fassung für einen Podcast: Zahlen und Kürzel ausgeschrieben, klingt gut vorgelesen, beginnt mit einer kurzen Begrüßung zum Konzert), "
         "wikipedia (exakter Titel des deutschen oder englischen Wikipedia-Artikels der Band bzw. des Künstlers, mit Sprache, z. B. 'en:Metallica'), "
         "farben (Objekt mit den Hex-Farben paper (sehr dunkler Hintergrund), paperWarm (etwas helleres Kartenfeld), ink (sehr heller Text), inkSoft (gedämpfter heller Text), accent (kräftige Markenfarbe der Band, gut sichtbar auf paper), gold (zweite Akzentfarbe), from und to (dunkler Farbverlauf für die Kopfzeile), "
         "font (genau eines von serif, sans, mono, schwer; passend zur Stimmung der Band)). Die Farben sollen zur Ästhetik der Band passen (Cover, Logo, Bühnenlook) und guten Kontrast haben. "
         "Regeln: Nur belegte Fakten, nichts erfinden, im Zweifel weglassen. Eigene Worte, keine Liedtexte, keine wörtlichen Zitate aus Quellen. Sachlich und respektvoll bei heiklen Themen.")
    return gemini(p)


def lieder(artist):
    p = (f"Recherchiere mit der Websuche die acht bekanntesten und für die Band wichtigsten Lieder von {artist} (mit unterschiedlichen Alben, ein Lied je Titel, keine Live- oder Remix-Versionen). "
         "Antworte NUR mit einem JSON-Objekt (ohne Markdown) der Form {\"songs\": [ ... ]}, jedes Element mit: "
         "title (bereinigter Titel), year (Erscheinungsjahr des ersten Release als Zahl), "
         "herkunft (Wer schrieb den Song, wie und wann entstand er; 50 bis 80 Wörter, eigene Worte), "
         "bedeutung (Worum geht es, verbreitete Deutung; 50 bis 80 Wörter, eigene Worte), "
         "fun (optional, ein belegtes Detail in 1 bis 2 Sätzen, sonst leere Zeichenkette). "
         "Regeln: Nur belegte Fakten. Keine Liedtexte, keine Zitate, keine wörtlichen Übernahmen. Bei heiklen Themen sachlich bleiben, keine Details zu Methoden.")
    return gemini(p)


def get_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Reiseblog-Konzertmodus/1.0 (thomas.skornia@gmail.com)"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def bild(wiki):
    """Hauptbild des Wikipedia-Artikels, nur wenn frei lizenziert. Gibt dict oder None zurück."""
    try:
        sprache, _, titel = (wiki or "").partition(":")
        if sprache not in ("de", "en") or not titel:
            sprache, titel = "en", wiki or ""
        u = (f"https://{sprache}.wikipedia.org/w/api.php?action=query&format=json&redirects=1&prop=pageimages&piprop=name&pilicense=free"
             f"&titles={urllib.parse.quote(titel)}")
        pages = get_json(u)["query"]["pages"]
        name = next(iter(pages.values())).get("pageimage")
        if not name:
            return None
        u = ("https://commons.wikimedia.org/w/api.php?action=query&format=json&prop=imageinfo&iiprop=extmetadata|url&titles="
             + urllib.parse.quote("File:" + name))
        info = next(iter(get_json(u)["query"]["pages"].values())).get("imageinfo", [{}])[0]
        md = info.get("extmetadata", {})
        strip = lambda s: re.sub(r"<[^>]+>", "", s or "").strip()[:120]
        return {"datei": name, "urheber": strip((md.get("Artist") or {}).get("value")) or "Wikimedia Commons",
                "lizenz": strip((md.get("LicenseShortName") or {}).get("value")),
                "seite": info.get("descriptionurl", "https://commons.wikimedia.org/wiki/File:" + urllib.parse.quote(name))}
    except Exception as e:  # noqa: BLE001
        print("Bild nicht gefunden:", e, flush=True)
        return None


def find_audio(node):
    found = []
    def walk(n):
        if isinstance(n, dict):
            if n.get("type") == "audio" and isinstance(n.get("data"), str):
                found.append(n["data"])
            for v in n.values():
                walk(v)
        elif isinstance(n, list):
            for v in n:
                walk(v)
    walk(node)
    return found[-1] if found else None


def sprache(text, out):
    body = {"model": TTS_MODEL, "input": [{"type": "user_input", "content": [{"type": "text", "text": text}]}],
            "response_format": {"type": "audio"}, "generation_config": {"speech_config": [{"voice": VOICE}]}}
    req = urllib.request.Request(TTS_ENDPOINT, data=json.dumps(body).encode(), method="POST",
                                 headers={"x-goog-api-key": KEY, "Content-Type": "application/json"})
    last = ""
    for versuch in range(3):
        try:
            with urllib.request.urlopen(req, timeout=240) as r:
                data = find_audio(json.load(r))
            if not data:
                raise RuntimeError("Antwort ohne Audio")
            raw = base64.b64decode(data)
            if raw[:4] != b"RIFF":
                buf = io.BytesIO()
                with wave.open(buf, "wb") as w:
                    w.setnchannels(1); w.setsampwidth(2); w.setframerate(24000); w.writeframes(raw)
                raw = buf.getvalue()
            subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", "pipe:0", "-ac", "1", "-ar", "24000", "-b:a", "48k", out], input=raw, check=True)
            return True
        except urllib.error.HTTPError as e:
            last = f"HTTP {e.code}"
            if e.code not in (429, 500, 503):
                break
        except Exception as e:  # noqa: BLE001
            last = str(e)
        time.sleep(5 * (versuch + 1))
    print("Sprachausgabe fehlgeschlagen:", last, flush=True)
    return False


def sauber(s, n):
    return re.sub(r"\s+\n", "\n", str(s or "")).strip()[:n]


def main():
    artist, city = eingabe()
    sl = slug(artist)
    datei = D(sl + ".json")
    os.makedirs(D(), exist_ok=True)
    print(f"Konzert: {artist} ({city}), Slug {sl}", flush=True)
    if os.path.exists(datei) and not os.environ.get("NEU"):
        print("Special gibt es schon, nichts zu tun (NEU=1 erzeugt neu).")
        return 0
    if not KEY:
        print("GEMINI_API_KEY fehlt."); return 1
    sp, qs1 = special(artist, city)
    time.sleep(8)
    ls, qs2 = lieder(artist)
    farben = {k: v for k, v in (sp.get("farben") or {}).items() if k in ("paper", "paperWarm", "ink", "inkSoft", "accent", "gold", "from", "to", "font")}
    farben = {k: v for k, v in farben.items() if (k == "font" and v in ("serif", "sans", "mono", "schwer")) or (k != "font" and isinstance(v, str) and HEX.match(v))}
    songs, ids = [], set()
    for s in ls.get("songs", []):
        t = sauber(s.get("title"), 80)
        if not t or not s.get("herkunft") or not s.get("bedeutung"):
            continue
        i = slug(t) or "lied"
        while i in ids:
            i += "-x"
        ids.add(i)
        j = {"id": i, "title": t, "year": s.get("year") if isinstance(s.get("year"), int) else None,
             "herkunft": sauber(s["herkunft"], 900), "bedeutung": sauber(s["bedeutung"], 900)}
        if s.get("fun"):
            j["fun"] = sauber(s["fun"], 300)
        songs.append(j)
    if len(songs) < 3 or not sp.get("text"):
        print("Zu wenig Inhalt von Gemini, nichts gespeichert."); return 1
    quellen, seen = [], set()
    for q in qs1 + qs2:
        if q["url"] not in seen:
            seen.add(q["url"]); quellen.append(q)
    out = {"slug": sl, "artist": artist, "city": city, "erstellt": HEUTE, "erzeugt_von": "Gemini (Google-Suche), nicht redaktionell geprüft",
           "theme": farben, "special": {"titel": sauber(sp.get("titel"), 90) or artist, "text": sauber(sp.get("text"), 6000), "sprech": sauber(sp.get("sprech") or sp.get("text"), 7000)},
           "bild": bild(sp.get("wikipedia")), "songs": songs[:10], "quellen": quellen[:25]}
    time.sleep(3)
    os.makedirs(os.path.join(ROOT, "audio"), exist_ok=True)
    if not sprache(out["special"]["sprech"], os.path.join(ROOT, "audio", f"konzert-{sl}.mp3")):
        print("Hinweis: Die Seite liest dann mit der Gerätestimme vor.")
    with open(datei, "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)
    try:
        idx = json.load(open(D("index.json"), encoding="utf-8"))
    except Exception:  # noqa: BLE001
        idx = []
    idx = [x for x in idx if x.get("slug") != sl] + [{"slug": sl, "artist": artist, "erstellt": HEUTE}]
    with open(D("index.json"), "w", encoding="utf-8") as fh:
        json.dump(idx, fh, ensure_ascii=False, indent=1)
    print(f"Fertig: {len(songs)} Lieder, Bild: {'ja' if out['bild'] else 'nein'}, Farben: {len(farben)} Werte")
    return 0


if __name__ == "__main__":
    sys.exit(main())
