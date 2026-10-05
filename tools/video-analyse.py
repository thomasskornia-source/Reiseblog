#!/usr/bin/env python3
"""Testlauf: YouTube-Beitrag mit Gemini auswerten (Indikatoren + Pfeil).

Braucht GEMINI_API_KEY und die Umgebungsvariable VIDEO_URL. Es wird KEIN Transkript gespeichert,
nur eine Auswertung in eigenen Worten mit höchstens zwei kurzen Zitaten. Ergebnis: auswertung/test.md
"""
import json, os, re, sys, time, urllib.request, urllib.error

KEY = os.environ.get("GEMINI_API_KEY", "").strip()
URL = os.environ.get("VIDEO_URL", "").strip()
MODELS = [m for m in [os.environ.get("GEMINI_VIDEO_MODEL", "").strip(), "gemini-3.8-flash", "gemini-3.7-flash", "gemini-flash-latest"] if m]
_m = re.search(r"(?:youtu\.be/|/live/|/shorts/|[?&]v=)([A-Za-z0-9_-]{11})", URL)
if _m:
    URL = "https://www.youtube.com/watch?v=" + _m.group(1)  # Standardform, nur die Video-ID
BASE = "https://generativelanguage.googleapis.com/v1beta"

PROMPT = """Du hörst einen täglichen deutschsprachigen Börsen-Beitrag (Marktstimmung, Börsenthemen).
Verstehe die Sicht des Sprechers. Gib KEIN Transkript wieder und schreibe nichts wörtlich ab,
höchstens zwei Zitate mit je unter 15 Wörtern. Antworte ausschließlich als JSON mit diesen Feldern:
- datum_thema: ein Satz, worum es heute geht
- indikatoren: Liste von Objekten {name, rolle, einschaetzung}; name = woran der Sprecher die Stimmung festmacht
  (z.B. Zinsen, Inflation, Ölpreis, VIX, Quartalszahlen, einzelne Aktien, Zölle, Charttechnik),
  rolle = warum ihm das wichtig ist (1 Satz), einschaetzung = positiv|negativ|neutral
- gesamtstimmung: ein bis zwei Sätze in eigenen Worten
- pfeil: "hoch" | "runter" | "seitwaerts" (deine Einschätzung der Stimmung des Sprechers für den Markt)
- begruendung: 2 Sätze, warum dieser Pfeil
- zitate: Liste mit höchstens zwei kurzen wörtlichen Zitaten
- sicherheit: hoch|mittel|niedrig (wie gut du den Beitrag verstanden hast)"""


def call(model):
    body = {
        "contents": [{"parts": [{"file_data": {"file_uri": URL}}, {"text": PROMPT}]}],
        "generationConfig": {"responseMimeType": "application/json", "temperature": 0.2},
    }
    req = urllib.request.Request(f"{BASE}/models/{model}:generateContent", data=json.dumps(body).encode(), method="POST",
                                 headers={"x-goog-api-key": KEY, "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=600) as r:
        return json.load(r)


def main():
    if not KEY or not URL:
        sys.exit("GEMINI_API_KEY oder VIDEO_URL fehlt")
    res, used, errors = None, None, []
    for m in MODELS:
        for attempt in range(2):
            try:
                res, used = call(m), m
                break
            except urllib.error.HTTPError as e:
                msg = f"{m}: HTTP {e.code} {e.read().decode(errors='replace')[:400]}"
                errors.append(msg); print(msg)
                if e.code in (429, 500, 503) and attempt == 0:
                    time.sleep(10); continue
                break
            except Exception as e:  # noqa: BLE001
                msg = f"{m}: {e}"; errors.append(msg); print(msg); break
        if res:
            break
    if not res:
        try:
            req = urllib.request.Request(f"{BASE}/models?pageSize=100", headers={"x-goog-api-key": KEY})
            names = [x["name"] for x in json.load(urllib.request.urlopen(req, timeout=60)).get("models", [])]
            print("Verfügbare Modelle:", ", ".join(n.replace("models/", "") for n in names))
        except Exception as e:  # noqa: BLE001
            print("Modellliste nicht lesbar:", e)
        sys.exit("Keine Auswertung möglich")
    usage = res.get("usageMetadata", {})
    text = res["candidates"][0]["content"]["parts"][0]["text"]
    data = json.loads(text)
    pf = {"hoch": "⬆️ hoch", "runter": "⬇️ runter", "seitwaerts": "➡️ seitwärts"}.get(data.get("pfeil"), data.get("pfeil"))
    out = [f"# Test-Auswertung", "", f"Quelle: {URL} (Beitrag von Markus Koch)", f"Modell: {used}, Tokens: {usage.get('totalTokenCount')}", "",
           f"**Thema:** {data.get('datum_thema')}", "", f"## Pfeil: {pf}", "", data.get("begruendung", ""), "",
           f"**Gesamtstimmung:** {data.get('gesamtstimmung')}", "", "## Indikatoren, die ihm wichtig sind", ""]
    for i in data.get("indikatoren", []):
        out.append(f"- **{i.get('name')}** ({i.get('einschaetzung')}): {i.get('rolle')}")
    out += ["", "## Kurze Zitate", ""] + [f"- „{z}“" for z in data.get("zitate", [])[:2]]
    out += ["", f"Sicherheit der Auswertung: {data.get('sicherheit')}", "",
            "_Eigene Zusammenfassung, kein Transkript. Stimmungsbild, keine Anlageberatung._"]
    os.makedirs("auswertung", exist_ok=True)
    open("auswertung/test.md", "w", encoding="utf-8").write("\n".join(out) + "\n")
    print("\n".join(out))


main()
