#!/usr/bin/env python3
"""Erzeugt zu jedem Song in data/songs.json eine Audiodatei audio/<id>.mp3 (Gemini-Sprachausgabe).

Braucht die Umgebungsvariable GEMINI_API_KEY und ffmpeg. Songs, zu denen es schon eine Datei gibt, werden übersprungen.
Schlägt ein Song fehl, läuft das Skript mit den übrigen weiter und beendet sich am Ende mit Fehlercode 1.
"""
import datetime, base64, io, json, os, subprocess, sys, time, urllib.request, urllib.error, wave

ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/interactions"
MODEL = os.environ.get("GEMINI_TTS_MODEL", "gemini-3.8-flash-tts")
VOICE = os.environ.get("GEMINI_TTS_VOICE", "Kore")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def text_for(s):
    t = f"{s['title']}, von {s['artist']}, {s['year']}. Woher kommt der Song? {s['herkunft']} Was bedeutet er? {s['bedeutung']}"
    if s.get("fun"):
        t += f" Noch ein Detail. {s['fun']}"
    return t


def find_audio(node):
    """Sucht im Antwort-JSON den letzten Audio-Block mit Base64-Daten."""
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


def request_audio(text, key):
    body = {
        "model": MODEL,
        "input": [{"type": "user_input", "content": [{"type": "text", "text": text}]}],
        "response_format": {"type": "audio"},
        "generation_config": {"speech_config": [{"voice": VOICE}]},
    }
    req = urllib.request.Request(ENDPOINT, data=json.dumps(body).encode(), method="POST",
                                 headers={"x-goog-api-key": key, "Content-Type": "application/json"})
    last = None
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=180) as r:
                data = find_audio(json.load(r))
                if data:
                    return base64.b64decode(data)
                raise RuntimeError("Antwort ohne Audio")
        except urllib.error.HTTPError as e:
            last = f"HTTP {e.code}: {e.read().decode(errors='replace')[:300]}"
            if e.code not in (429, 500, 503):
                break
        except Exception as e:  # noqa: BLE001
            last = str(e)
        time.sleep(5 * (attempt + 1))
    raise RuntimeError(last)


def to_wav(raw):
    if raw[:4] == b"RIFF":
        return raw
    buf = io.BytesIO()  # Rohdaten: 16 Bit, 24 kHz, mono
    with wave.open(buf, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(24000); w.writeframes(raw)
    return buf.getvalue()


def main():
    key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not key:
        print("GEMINI_API_KEY fehlt (GitHub: Settings > Secrets and variables > Actions). Es wird nichts erzeugt, die Seite liest dann mit der Gerätestimme vor.")
        sys.exit(0)
    songs = json.load(open(os.path.join(ROOT, "data", "songs.json"), encoding="utf-8"))
    os.makedirs(os.path.join(ROOT, "audio"), exist_ok=True)
    failed = 0
    for s in songs:
        if not s.get("id") or not s.get("herkunft"):
            continue
        out = os.path.join(ROOT, "audio", s["id"] + ".mp3")
        if os.path.exists(out):
            continue
        try:  # ältere Songs bekommen keine Sprachdatei mehr (wird nach 14 Tagen aufgeräumt, tools/aufraeumen.py)
            if (datetime.date.today() - datetime.date.fromisoformat(s.get("date", ""))).days > 14:
                continue
        except ValueError:
            pass
        try:
            wav = to_wav(request_audio(text_for(s), key))
            subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", "pipe:0", "-ac", "1", "-ar", "24000", "-b:a", "48k", out],
                           input=wav, check=True)
            print("ok", s["id"], os.path.getsize(out), "Bytes")
        except Exception as e:  # noqa: BLE001
            failed += 1
            print("FEHLER", s["id"], e, file=sys.stderr)
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
