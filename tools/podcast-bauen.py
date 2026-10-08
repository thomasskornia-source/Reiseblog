#!/usr/bin/env python3
"""Täglicher persönlicher Podcast (ca. 12 Minuten, Deutsch).

Ablauf: neue YouTube-Videos der eigenen Kanäle (Gemini wertet das Video direkt aus, kein Transkript wird gespeichert)
+ Marktlage (data/markt.json, data/koch.json, Yahoo) + eigene Aktien (PODCAST_TICKER) + Wetter (Open-Meteo)
-> Sprechtext (Gemini) -> Sprachausgabe (Gemini TTS) -> MP3 -> Feed (RSS).

Umgebungsvariablen:
  GEMINI_API_KEY   (Pflicht)
  PODCAST_TICKER   Yahoo-Ticker, durch Komma getrennt, z. B. "AMZN,GOOGL,SAP.DE,BRK-B,TTWO,AVGO" (GitHub-Secret/Variable, nicht im Repo)
  PODCAST_TOKEN    geheimer Teil der Feed-Adresse (GitHub-Secret)
  PODCAST_AUDIO_BASE  Basis-URL der MP3-Dateien (Release-Downloads); Standard siehe unten
  GEMINI_TTS_VOICE (Standard Kore, weiblich), GEMINI_TTS_MODEL
  TROCKENLAUF=1    nur Sprechtext erzeugen (kein Audio, kein Feed)
Ergebnis: podcast/<TOKEN>/feed.xml, podcast/<TOKEN>/episoden.json, podcast/neu/<datum>.mp3 (wird vom Workflow als Release hochgeladen)
"""
import base64, datetime as dt, html, io, json, os, re, subprocess, sys, time, urllib.parse, urllib.request, urllib.error, wave
import xml.etree.ElementTree as ET
import zoneinfo

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
KEY = os.environ.get("GEMINI_API_KEY", "").strip()
TICKER = [t.strip() for t in os.environ.get("PODCAST_TICKER", "").split(",") if t.strip()]
TOKEN = os.environ.get("PODCAST_TOKEN", "").strip() or "entwurf"
TROCKEN = os.environ.get("TROCKENLAUF") == "1"
REPO = os.environ.get("GITHUB_REPOSITORY", "thomasskornia-source/Reiseblog")
SEITE = "https://%s.github.io/%s" % tuple(REPO.split("/"))
AUDIO_BASE = os.environ.get("PODCAST_AUDIO_BASE", "https://github.com/%s/releases/download" % REPO)
BASE = "https://generativelanguage.googleapis.com/v1beta"
MODELS = [m for m in [os.environ.get("GEMINI_VIDEO_MODEL", "").strip(), "gemini-3.8-flash", "gemini-3.7-flash", "gemini-flash-latest"] if m]
TTS_MODEL = os.environ.get("GEMINI_TTS_MODEL", "gemini-3.8-flash-tts")
VOICE = os.environ.get("GEMINI_TTS_VOICE", "Kore")
BERLIN = zoneinfo.ZoneInfo("Europe/Berlin")
UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36",
      "Accept-Language": "de-DE,de;q=0.9", "Cookie": "CONSENT=YES+1; SOCS=CAI"}
MAX_VIDEOS, MAX_ALTER_H, BEHALTEN_TAGE = 6, 36, 14
ORT = ("Eichenau", 48.17, 11.32)
TAGE = ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"]
MONATE = ["Januar", "Februar", "März", "April", "Mai", "Juni", "Juli", "August", "September", "Oktober", "November", "Dezember"]

PODCAST_DIR = os.path.join(ROOT, "podcast")
KANAELE = os.path.join(ROOT, "data", "podcast-kanaele.json")
GESEHEN = os.path.join(ROOT, "data", "podcast-gesehen.json")
FEED_DIR = os.path.join(PODCAST_DIR, TOKEN)


def log(*a):
    print(*a, flush=True)


def get(url, binary=False):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
        b = r.read()
    return b if binary else b.decode("utf-8", "replace")


def laden(pfad, standard):
    try:
        return json.load(open(pfad, encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return standard


def speichern(pfad, obj):
    os.makedirs(os.path.dirname(pfad), exist_ok=True)
    json.dump(obj, open(pfad, "w", encoding="utf-8"), ensure_ascii=False, indent=1)


# ---------------------------------------------------------------- YouTube
def kanaele():
    """Handle -> Channel-ID (einmal ermittelt, dann gemerkt in data/podcast-kanaele.json)."""
    db = laden(KANAELE, {"kanaele": []})
    fertig = {k["handle"]: k for k in db["kanaele"]}
    handles = [h.strip().lstrip("@") for h in os.environ.get("PODCAST_KANAELE", "pboyle,newmoneyyoutube,theprofgpod,lynxbrokergermany,creativeplanning,jamesbulltard").split(",") if h.strip()]
    neu = False
    for h in handles:
        if h in fertig and fertig[h].get("id"):
            continue
        try:
            seite = get("https://www.youtube.com/@%s" % h)
            m = re.search(r'"(?:channelId|externalId)":"(UC[\w-]{22})"', seite) or re.search(r'channel/(UC[\w-]{22})', seite)
            n = re.search(r'<meta property="og:title" content="([^"]*)"', seite)
            fertig[h] = {"handle": h, "id": m.group(1) if m else None, "name": html.unescape(n.group(1)) if n else h}
            neu = True
            log("Kanal", h, "->", fertig[h]["id"])
        except Exception as e:  # noqa: BLE001
            log("Kanal nicht lesbar:", h, e)
    if neu:
        speichern(KANAELE, {"kanaele": [fertig[h] for h in handles if h in fertig]})
    return [fertig[h] for h in handles if h in fertig and fertig[h].get("id")]


def neue_videos(kan, gesehen):
    ns = {"a": "http://www.w3.org/2005/Atom", "y": "http://www.youtube.com/xml/schemas/2015"}
    jetzt = dt.datetime.now(dt.timezone.utc)
    out = []
    for k in kan:
        try:
            x = ET.fromstring(get("https://www.youtube.com/feeds/videos.xml?channel_id=%s" % k["id"], True))
        except Exception as e:  # noqa: BLE001
            log("Feed nicht lesbar:", k["handle"], e); continue
        for e in x.findall("a:entry", ns):
            vid = e.find("y:videoId", ns).text
            zeit = dt.datetime.fromisoformat(e.find("a:published", ns).text.replace("Z", "+00:00"))
            if vid in gesehen or (jetzt - zeit).total_seconds() > MAX_ALTER_H * 3600:
                continue
            titel = e.find("a:title", ns).text
            if "/shorts/" in (e.find("a:link", ns).get("href") or ""):
                continue
            out.append({"id": vid, "titel": titel, "kanal": k["name"], "handle": k["handle"], "zeit": zeit.isoformat()})
    out.sort(key=lambda v: v["zeit"], reverse=True)
    return out[:MAX_VIDEOS]


# ---------------------------------------------------------------- Gemini
def gemini(parts, json_antwort=False, temperatur=0.4, timeout=900):
    body = {"contents": [{"parts": parts}], "generationConfig": {"temperature": temperatur}}
    if json_antwort:
        body["generationConfig"]["responseMimeType"] = "application/json"
    fehler = []
    for m in MODELS:
        for versuch in range(2):
            req = urllib.request.Request("%s/models/%s:generateContent" % (BASE, m), data=json.dumps(body).encode(), method="POST",
                                         headers={"x-goog-api-key": KEY, "Content-Type": "application/json"})
            try:
                with urllib.request.urlopen(req, timeout=timeout) as r:
                    res = json.load(r)
                txt = res["candidates"][0]["content"]["parts"][0]["text"].strip()
                if json_antwort:
                    txt = json.loads(re.sub(r"^```(?:json)?|```$", "", txt).strip())
                return txt
            except urllib.error.HTTPError as e:
                msg = "%s: HTTP %s %s" % (m, e.code, e.read().decode(errors="replace")[:200])
                fehler.append(msg); log(msg)
                if e.code in (429, 500, 503) and versuch == 0:
                    time.sleep(20); continue
                break
            except Exception as e:  # noqa: BLE001
                fehler.append("%s: %s" % (m, e)); log(fehler[-1]); break
    raise RuntimeError(fehler[-1] if fehler else "keine Antwort")


VIDEO_PROMPT = """Du hörst ein YouTube-Video (meist englisch). Fasse es für einen deutschsprachigen Podcast zusammen. Schreibe nichts wörtlich ab
und gib kein Transkript wieder; alles in eigenen Worten, Deutsch. Antworte ausschließlich als JSON:
- relevant: true, wenn es um Wirtschaft, Börse, Geldanlage, Finanzen oder Investieren geht, sonst false
- kernaussage: ein Satz, worum es geht
- punkte: Liste mit 3 bis 5 kurzen Punkten (je ein bis zwei Sätze): die wichtigsten Aussagen, Zahlen und Schlussfolgerungen
- mitnehmen: ein Satz, was man daraus mitnehmen kann
- erwaehnte_titel: Liste der Aktien/ETFs/Rohstoffe, die als Hauptthema vorkommen (leer, wenn keine)"""


def video_auswerten(v):
    return gemini([{"file_data": {"file_uri": "https://www.youtube.com/watch?v=%s" % v["id"]}}, {"text": VIDEO_PROMPT}], json_antwort=True, temperatur=0.2)


# ---------------------------------------------------------------- Märkte, Aktien, Wetter
def kurs_aenderung(ticker):
    import trend
    meta, z = trend.holen(ticker, "10d")
    if len(z) < 2:
        raise RuntimeError("zu wenig Kurse")
    letzt, vor = z[-1][4], z[-2][4]
    tag = dt.datetime.fromtimestamp(z[-1][0], BERLIN).strftime("%d.%m.")
    return {"ticker": ticker, "name": meta.get("shortName") or meta.get("longName") or ticker, "kurs": round(letzt, 2),
            "waehrung": meta.get("currency"), "aenderung_pct": round((letzt / vor - 1) * 100, 2), "stand": tag}


def maerkte():
    out = []
    for t, n in (("^GSPC", "S&P 500"), ("^IXIC", "Nasdaq Composite"), ("^GDAXI", "DAX")):
        try:
            d = kurs_aenderung(t); d["name"] = n; out.append(d)
        except Exception as e:  # noqa: BLE001
            log("Index nicht abrufbar:", t, e)
    return out


def aktien():
    out = []
    for t in TICKER:
        try:
            out.append(kurs_aenderung(t))
        except Exception as e:  # noqa: BLE001
            log("Aktie nicht abrufbar:", t, e)
    return out


def trend_und_stimmung():
    m = laden(os.path.join(ROOT, "data", "markt.json"), {})
    k = laden(os.path.join(ROOT, "data", "koch.json"), {"beitraege": []})
    b = (k.get("beitraege") or [None])[0]
    return ({"stand": m.get("stand"), "ampel": m.get("ampel"), "lage": m.get("lage"), "rsi": m.get("rsi")} if m else None,
            {"datum": b.get("datum"), "score": b.get("score"), "thema": b.get("thema"), "gesamtstimmung": b.get("gesamtstimmung")} if b else None)


WETTERCODE = {0: "klar", 1: "überwiegend klar", 2: "wolkig", 3: "bedeckt", 45: "Nebel", 48: "Raureifnebel", 51: "leichter Nieselregen", 53: "Nieselregen",
              55: "starker Nieselregen", 61: "leichter Regen", 63: "Regen", 65: "starker Regen", 71: "leichter Schneefall", 73: "Schneefall",
              75: "starker Schneefall", 80: "leichte Schauer", 81: "Schauer", 82: "kräftige Schauer", 95: "Gewitter", 96: "Gewitter mit Hagel", 99: "Gewitter mit Hagel"}


def wetter():
    url = ("https://api.open-meteo.com/v1/forecast?latitude=%s&longitude=%s&timezone=Europe%%2FBerlin&forecast_days=1"
           "&daily=temperature_2m_max,temperature_2m_min,precipitation_sum,precipitation_probability_max,wind_speed_10m_max,weather_code,sunrise,sunset"
           "&hourly=temperature_2m,precipitation" % (ORT[1], ORT[2]))
    j = json.loads(get(url))
    d = j["daily"]
    h = j["hourly"]
    regen_stunden = [x[11:16] for x, p in zip(h["time"], h["precipitation"]) if (p or 0) >= 0.2 and 7 <= int(x[11:13]) <= 20]
    return {"ort": ORT[0], "beschreibung": WETTERCODE.get(d["weather_code"][0], "wechselhaft"), "max": d["temperature_2m_max"][0], "min": d["temperature_2m_min"][0],
            "regen_mm": d["precipitation_sum"][0], "regen_wahrscheinlichkeit_pct": d["precipitation_probability_max"][0], "wind_max_kmh": d["wind_speed_10m_max"][0],
            "sonnenaufgang": d["sunrise"][0][11:], "sonnenuntergang": d["sunset"][0][11:], "regen_zwischen_7_und_20_uhr": regen_stunden}


# ---------------------------------------------------------------- Sprechtext
SKRIPT_PROMPT = """Schreibe das Sprechskript für die heutige Folge eines persönlichen Podcasts für Andrea (53, lebt in Eichenau bei München, hat einen Labrador
und ein Islandpferd, lacht gern, kommt aus dem Münsterland/Ruhrgebiet). Ton: warmherzig, locker, mit trockenem Humor, wie eine kluge Freundin, die
beim Kaffee berichtet. Duze Andrea. Kein Fachjargon-Wust, Fachbegriffe kurz erklären.

LÄNGE: etwa 1800 Wörter (das sind rund 12 Minuten gesprochen). Nicht deutlich kürzer.
REIHENFOLGE (genau so, ohne Überschriften im Text, aber mit der Zeile ###ABSCHNITT### zwischen den Abschnitten):
1. Begrüßung mit Wochentag und Datum, ein kurzer Aufhänger.
2. YouTube-Highlights: jedes Video mit Kanalname, worum es geht, die wichtigsten Punkte und was man mitnehmen kann. Gibt es keine neuen Videos, sage das ehrlich
   in einem Satz und gehe zügig weiter. Nur Videos aus der Liste, nichts dazuerfinden.
3. Marktlage-Wrap-up: Indizes (S&P 500, Nasdaq, DAX) mit Tagesveränderung, Trend-Ampel des S&P 500 (Up/Medium/Down) und Stimmung von Markus Koch, wenn vorhanden.
   Am Wochenende oder nach Feiertagen: sagen, dass die Börsen geschlossen waren und der Stand vom letzten Handelstag ist.
4. Andreas Aktien: kurz je Aktie Kurs und Veränderung zum Vortag, danach ein Satz zur Einordnung (z. B. wer heraussticht). KEINE Kauf-, Verkaufs- oder
   Halteempfehlung, keine Kursziele, keine Prognosen. Kurz erwähnen, dass es ein Überblick und keine Anlageberatung ist.
5. Wetter für Eichenau: Temperatur, Regen, Wind und ein praktischer Tipp (Gassi mit dem Labrador, Ausritt mit dem Islandpferd).
6. Verabschiedung in ein bis zwei Sätzen.

REGELN:
- Nur Fakten aus den gelieferten Daten verwenden. Nichts erfinden, keine Nachrichten dazu dichten. Fehlen Daten, den Teil kurz überspringen oder ehrlich benennen.
- Alles in eigenen Worten, keine wörtlichen Zitate aus den Videos.
- Gut sprechbar: Zahlen als gesprochene Zahlen ("plus zwei Komma drei Prozent", "rund neunzehn Grad"), keine Tabellen, keine Aufzählungszeichen, keine Klammern,
  keine Emojis, keine Markdown-Zeichen. Tickerkürzel als Firmennamen aussprechen (Amazon, Alphabet, SAP, Berkshire Hathaway, Take-Two, Broadcom).
- Währungen: US-Aktien in Dollar, SAP in Euro.

DATEN (JSON):
%s"""


def sprechtext(daten):
    txt = gemini([{"text": SKRIPT_PROMPT % json.dumps(daten, ensure_ascii=False, indent=1)}], temperatur=0.7)
    txt = re.sub(r"[*_#]{1,3}(?!ABSCHNITT)", "", txt.replace("###ABSCHNITT###", "§§")).replace("§§", "\n\n")
    return re.sub(r"\n{3,}", "\n\n", txt).strip()


# ---------------------------------------------------------------- Audio
def tts(text):
    body = {"model": TTS_MODEL, "input": [{"type": "user_input", "content": [{"type": "text", "text": text}]}],
            "response_format": {"type": "audio"}, "generation_config": {"speech_config": [{"voice": VOICE}]}}
    letzt = None
    for versuch in range(5):
        req = urllib.request.Request(BASE + "/interactions", data=json.dumps(body).encode(), method="POST",
                                     headers={"x-goog-api-key": KEY, "Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=240) as r:
                j = json.load(r)
            gefunden = []
            def walk(n):
                if isinstance(n, dict):
                    if n.get("type") == "audio" and isinstance(n.get("data"), str):
                        gefunden.append(n["data"])
                    for v in n.values(): walk(v)
                elif isinstance(n, list):
                    for v in n: walk(v)
            walk(j)
            if not gefunden:
                raise RuntimeError("Antwort ohne Audio")
            return base64.b64decode(gefunden[-1])
        except urllib.error.HTTPError as e:
            letzt = "HTTP %s %s" % (e.code, e.read().decode(errors="replace")[:200])
            if e.code not in (429, 500, 503):
                break
        except Exception as e:  # noqa: BLE001
            letzt = str(e)
        time.sleep(15 * (versuch + 1))
    raise RuntimeError(letzt)


def zu_wav(raw):
    if raw[:4] == b"RIFF":
        return raw
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(24000); w.writeframes(raw)
    return buf.getvalue()


def brocken(text, maxlen=1400):
    """Absätze zu Blöcken bis etwa maxlen Zeichen bündeln (ein TTS-Aufruf je Block)."""
    out, cur = [], ""
    for p in [p.strip() for p in text.split("\n\n") if p.strip()]:
        if cur and len(cur) + len(p) > maxlen:
            out.append(cur); cur = p
        else:
            cur = (cur + "\n\n" + p) if cur else p
    if cur:
        out.append(cur)
    return out


def audio_bauen(text, ziel):
    teile = []
    for i, b in enumerate(brocken(text)):
        log("Sprachausgabe Block", i + 1)
        teile.append(zu_wav(tts(b)))
        time.sleep(3)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as out:
        for i, t in enumerate(teile):
            with wave.open(io.BytesIO(t)) as w:
                if i == 0:
                    out.setparams(w.getparams())
                out.writeframes(w.readframes(w.getnframes()))
                out.writeframes(b"\x00" * int(w.getframerate() * w.getsampwidth() * 0.4))  # kurze Pause zwischen den Blöcken
    os.makedirs(os.path.dirname(ziel), exist_ok=True)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", "pipe:0", "-ac", "1", "-ar", "24000", "-b:a", "48k", ziel], input=buf.getvalue(), check=True)
    dauer = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", ziel], capture_output=True, text=True).stdout.strip() or 0)
    return dauer


# ---------------------------------------------------------------- Feed
def feed_schreiben(episoden):
    os.makedirs(FEED_DIR, exist_ok=True)
    feed_url = "%s/podcast/%s/feed.xml" % (SEITE, TOKEN)
    e = html.escape
    items = []
    for ep in sorted(episoden, key=lambda x: x["datum"], reverse=True):
        d = dt.datetime.fromisoformat(ep["zeit"])
        m, s = divmod(int(ep.get("dauer") or 0), 60)
        items.append("""    <item>
      <title>%s</title>
      <description>%s</description>
      <pubDate>%s</pubDate>
      <guid isPermaLink="false">%s</guid>
      <enclosure url="%s" length="%d" type="audio/mpeg"/>
      <itunes:duration>%d:%02d</itunes:duration>
    </item>""" % (e(ep["titel"]), e(ep.get("beschreibung", "")), d.strftime("%a, %d %b %Y %H:%M:%S +0000"), e(ep["id"]), e(ep["url"]), ep["groesse"], m, s))
    xml = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd">
  <channel>
    <title>Andreas Morgenpodcast</title>
    <link>%s</link>
    <language>de</language>
    <description>Persönlicher täglicher Podcast: YouTube-Highlights, Marktlage, eigene Aktien und Wetter für Eichenau.</description>
    <itunes:author>Andrea</itunes:author>
    <itunes:explicit>false</itunes:explicit>
    <itunes:block>Yes</itunes:block>
%s
  </channel>
</rss>
""" % (e(feed_url), "\n".join(items))
    open(os.path.join(FEED_DIR, "feed.xml"), "w", encoding="utf-8").write(xml)
    speichern(os.path.join(FEED_DIR, "episoden.json"), episoden)
    return feed_url


# ---------------------------------------------------------------- Hauptprogramm
def main():
    if not KEY:
        sys.exit("GEMINI_API_KEY fehlt")
    jetzt = dt.datetime.now(BERLIN)
    datum = jetzt.strftime("%Y-%m-%d")
    wochentag = "%s, %d. %s %d" % (TAGE[jetzt.weekday()], jetzt.day, MONATE[jetzt.month - 1], jetzt.year)
    gesehen = laden(GESEHEN, [])

    videos = []
    for v in neue_videos(kanaele(), gesehen):
        log("Video:", v["kanal"], "|", v["titel"][:70])
        try:
            a = video_auswerten(v)
        except Exception as e:  # noqa: BLE001
            log("  nicht ausgewertet, wird morgen noch einmal versucht:", str(e)[:160]); continue
        gesehen.append(v["id"])
        if a.get("relevant", True):
            videos.append({"kanal": v["kanal"], "titel": v["titel"], **{k: a.get(k) for k in ("kernaussage", "punkte", "mitnehmen", "erwaehnte_titel")}})
    if not TICKER:
        log("Hinweis: PODCAST_TICKER ist leer, der Aktienteil entfällt.")
    ampel, koch = trend_und_stimmung()
    try:
        w = wetter()
    except Exception as e:  # noqa: BLE001
        log("Wetter nicht abrufbar:", e); w = None
    daten = {"heute": wochentag, "uhrzeit": "06:00", "youtube_videos": videos, "indizes": maerkte(), "sp500_trend": ampel, "markus_koch_stimmung": koch,
             "andreas_aktien": aktien(), "wetter": w}
    text = sprechtext(daten)
    log("Sprechtext: %d Wörter" % len(text.split()))
    os.makedirs(os.path.join(ROOT, "auswertung"), exist_ok=True)
    if TROCKEN:
        print("\n" + text)
        return

    ziel = os.path.join(PODCAST_DIR, "neu", datum + ".mp3")
    dauer = audio_bauen(text, ziel)
    log("Audio: %.1f Minuten, %d Bytes" % (dauer / 60, os.path.getsize(ziel)))
    tag = "podcast-%s-%s" % (TOKEN, datum)
    episoden = laden(os.path.join(FEED_DIR, "episoden.json"), [])
    episoden = [e for e in episoden if e["datum"] != datum]
    episoden.append({"id": tag, "datum": datum, "zeit": dt.datetime.now(dt.timezone.utc).isoformat(), "titel": "Morgenpodcast %s" % wochentag,
                     "beschreibung": "Heute: %s." % (", ".join(v["kanal"] for v in videos) or "Marktlage, Aktien und Wetter"),
                     "url": "%s/%s/%s.mp3" % (AUDIO_BASE, tag, datum), "groesse": os.path.getsize(ziel), "dauer": dauer})
    grenze = str(jetzt.date() - dt.timedelta(days=BEHALTEN_TAGE))
    alt = [e["id"] for e in episoden if e["datum"] < grenze]
    episoden = [e for e in episoden if e["datum"] >= grenze]
    speichern(GESEHEN, gesehen[-400:])
    log("Feed:", feed_schreiben(episoden))
    speichern(os.path.join(PODCAST_DIR, "neu", "tag.json"), {"tag": tag, "datei": datum + ".mp3", "alt": alt})
    # der Sprechtext bleibt nur im Lauf-Log (nicht im Repo)
    open(os.path.join(ROOT, "auswertung", "podcast-letzter-text.txt"), "w", encoding="utf-8").write(text)


if __name__ == "__main__":
    main()
