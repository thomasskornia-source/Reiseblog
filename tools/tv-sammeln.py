#!/usr/bin/env python3
"""TV heute: holt das Abendprogramm (19:30–22:00, ohne Nachrichten) und ersetzt die TV-Einträge in data/vergnuegen.json.
Läuft täglich über .github/workflows/tv.yml. Alte Einträge bleiben, wenn der Abruf fehlschlägt (kein leerer Bildschirm).
Keine Texte Dritter: nur Titel, Zeit, Sender und eigene Kurzfassung. Braucht GEMINI_API_KEY."""
import datetime as dt, hashlib, html, json, os, re, sys, time, urllib.request, urllib.error

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D = lambda n: os.path.join(ROOT, "data", n)
KEY = os.environ.get("GEMINI_API_KEY", "").strip()
UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36", "Accept-Language": "de-DE,de;q=0.9"}
MODELS = ["gemini-3.8-flash", "gemini-flash-latest"]
BASE = "https://generativelanguage.googleapis.com/v1beta"
HEUTE = dt.datetime.now(dt.timezone(dt.timedelta(hours=2 if 3 < dt.date.today().month < 11 else 1))).date()
SENDER = ["Das Erste", "ZDF", "BR", "WDR", "NDR", "hr", "SWR", "ARTE", "3sat"]
HOME = {"Das Erste": "https://www.daserste.de/", "ZDF": "https://www.zdf.de/", "BR": "https://www.br.de/fernsehen/", "WDR": "https://www1.wdr.de/fernsehen/",
        "NDR": "https://www.ndr.de/fernsehen/", "hr": "https://www.hr-fernsehen.de/", "SWR": "https://www.swrfernsehen.de/", "ARTE": "https://www.arte.tv/de/", "3sat": "https://www.3sat.de/"}
QUELLEN = [("tvinfo.de", "https://www.tvinfo.de/tv-programm"), ("tv-programmheute.de", "https://www.tv-programmheute.de/"),
           # prisma.de sperrt die GitHub-Server (403) und wurde entfernt. Kandidaten für die Regionalsender, was nicht lesbar ist, steht im Log:
           ("tvspielfilm.de", "https://www.tvspielfilm.de/tv-programm/sendungen/abends.html"), ("tvspielfilm.de", "https://www.tvspielfilm.de/tv-programm/sendungen/?time=prime&channel=BR"),
           ("fernsehserien.de", "https://www.fernsehserien.de/tv-programm/br"), ("fernsehserien.de", "https://www.fernsehserien.de/tv-programm/ndr"),
           ("fernsehserien.de", "https://www.fernsehserien.de/tv-programm/hr"), ("fernsehserien.de", "https://www.fernsehserien.de/tv-programm/wdr"), ("fernsehserien.de", "https://www.fernsehserien.de/tv-programm/swr"),
           ("hoerzu.de", "https://www.hoerzu.de/tv-programm/jetzt/"), ("tv.de", "https://www.tv.de/programm/"),
           ("programm.ard.de", "https://programm.ard.de/TV/Programm/Alle-Sender/"), ("br.de", "https://www.br.de/fernsehen/br-fernsehen/programm/index.html"),
           ("ndr.de", "https://www.ndr.de/fernsehen/programm/index.html"), ("hr-fernsehen.de", "https://www.hr-fernsehen.de/programm/"), ("wdr.de", "https://www1.wdr.de/fernsehen/programm/index.html")]


def get(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=45) as r:
        return r.read().decode("utf-8", "replace")


def text_von(h, n=7000):
    h = re.sub(r"(?is)<(script|style|noscript|svg|nav|footer|header)\b.*?</\1>", " ", h)
    h = re.sub(r"(?i)</(p|div|li|h\d|tr|br|section|article)>", "\n", h)
    t = html.unescape(re.sub(r"<[^>]+>", " ", h))
    t = re.sub(r"[ \t\r\f\v]+", " ", t)
    return re.sub(r"\n\s*\n+", "\n", t).strip()[:n]


def gemini(p):
    body = {"contents": [{"parts": [{"text": p}]}], "generationConfig": {"responseMimeType": "application/json", "temperature": 0.1}}
    fehler = ""
    for m in MODELS:
        for versuch in range(3):
            req = urllib.request.Request(f"{BASE}/models/{m}:generateContent", data=json.dumps(body).encode(), method="POST",
                                         headers={"x-goog-api-key": KEY, "Content-Type": "application/json"})
            try:
                with urllib.request.urlopen(req, timeout=90) as r:
                    t = json.load(r)["candidates"][0]["content"]["parts"][0]["text"].strip()
                return json.loads(re.sub(r"^```(?:json)?|```$", "", t).strip())
            except urllib.error.HTTPError as e:
                fehler = f"{m}: HTTP {e.code}"; print(fehler, flush=True)
                if e.code in (429, 500, 502, 503, 504) and versuch < 2:
                    time.sleep(60 * (versuch + 1)); continue
                break
            except Exception as e:  # noqa: BLE001
                fehler = f"{m}: {e}"; print(fehler, flush=True); break
    raise RuntimeError(fehler)


def sammeln():
    teile, quellen = [], {}
    for name, url in QUELLEN:
        try:
            t = text_von(get(url))
            if len(t) > 300:
                print("Quelle ok", len(t), "Zeichen", "mit 20:15" if "20:15" in t else "ohne 20:15", url, flush=True)
                teile.append(f"### Quelle {name} ({url})\n{t}")
                quellen[name] = url
        except Exception as e:  # noqa: BLE001
            print("Quelle fehlt", url, str(e)[:100], flush=True)
    return "\n\n".join(teile), quellen


def main():
    if not KEY:
        print("GEMINI_API_KEY fehlt."); return 0
    text, quellen = sammeln()
    if not text:
        print("Keine Quelle lesbar, alte Einträge bleiben."); return 0
    p = (f"Heute ist {HEUTE.isoformat()}. Aus den Programmseiten unten: gib das Abendprogramm von 19:30 bis 22:00 Uhr deutscher Zeit für diese Sender als JSON-Liste: "
         f"{', '.join(SENDER)}. Nur Sendungen von HEUTE. Alle Sendungen außer Nachrichten (Tagesschau, heute, Wetter, Regionalmagazine). Fehlt ein Sender in den Seiten, lass ihn weg, erfinde nichts. "
         "Jedes Objekt: titel (Sendungstitel, ggf. mit Folge), sender (genau einer der genannten), zeit (HH:MM), art (Film, Serie, Doku oder Show), "
         "kurz (EIGENE Kurzfassung in höchstens 150 Zeichen, nicht abgeschrieben; nur was die Seite sagt, sonst Genre und Dauer), quelle (Name der Seite, z. B. tvinfo.de). "
         "Höchstens 4 Sendungen je Sender. Antworte nur mit der JSON-Liste.\n\n" + text)
    try:
        items = gemini(p)
    except Exception as e:  # noqa: BLE001
        print("Gemini-Fehler:", str(e)[:200]); return 0
    if not isinstance(items, list):
        print("keine Liste", str(items)[:200]); return 0
    neu = []
    for it in items:
        if not isinstance(it, dict) or it.get("sender") not in SENDER or not it.get("titel") or not re.fullmatch(r"\d\d:\d\d", it.get("zeit") or ""):
            continue
        if not ("19:30" <= it["zeit"] <= "22:00"):
            continue
        s, art = it["sender"], it.get("art") if it.get("art") in ("Film", "Serie", "Doku", "Show") else ""
        iid = "tv-" + hashlib.sha1(f"{s}{it['titel']}{HEUTE}{it['zeit']}".encode()).hexdigest()[:10]
        neu.append({"id": iid, "rubrik": "tv", "titel": it["titel"].strip()[:120], "ort": s, "adresse": "", "datum": HEUTE.isoformat(), "datum_bis": "",
                    "zeit": it["zeit"], "preis": "", "dauer": "", "kurz": ((it.get("kurz") or "").strip()[:170] + " Programm kann sich ändern.").strip(),
                    "tags": [art] if art else [], "quelle": it.get("quelle") if it.get("quelle") in quellen else "tvinfo.de", "url": HOME[s],
                    "stand": HEUTE.isoformat(), "thema": s})
    print(len(neu), "Sendungen für heute")
    if len(neu) < 1:
        print("Nichts erkannt, alte Einträge bleiben."); return 0
    db = json.load(open(D("vergnuegen.json"), encoding="utf-8"))
    gesehen = {x["thema"] for x in neu}
    print("Sender heute:", sorted(gesehen), "| fehlend:", sorted(set(SENDER) - gesehen))
    # Sender ohne neue Treffer behalten ihre heutigen Einträge (aus früherem Lauf), alles Ältere fliegt raus
    db = [x for x in db if x.get("rubrik") != "tv" or (x.get("datum") == HEUTE.isoformat() and x.get("thema") not in gesehen)] + sorted(neu, key=lambda x: (x["thema"], x["zeit"]))
    json.dump(db, open(D("vergnuegen.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:  # noqa: BLE001
        import traceback; traceback.print_exc(); sys.exit(0)   # Lauf bleibt grün, Fehler steht im Log
