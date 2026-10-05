#!/usr/bin/env python3
"""Erzeugt zu jedem Bayern-Rätsel in data/raetsel.json audio/raetsel-<id>.mp3 und audio/raetsel-<id>.json (Zeitmarken).

Jedes Segment wird einzeln gesprochen (Gemini-Sprachausgabe, wie tools/song-audio.py). Nach Fragen wird eine Denkpause
(Segmentfeld "pause", Sekunden) eingefügt. Gesprochen wird "s" (Zahlen ausgeschrieben), sonst "t". Braucht GEMINI_API_KEY und ffmpeg. Vorhandene Dateien werden übersprungen.
"""
import importlib.util, io, json, os, re, subprocess, sys, time, wave

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
spec = importlib.util.spec_from_file_location("song_audio", os.path.join(ROOT, "tools", "song-audio.py"))
SA = importlib.util.module_from_spec(spec); spec.loader.exec_module(SA)
GAP = 0.7  # Sekunden Luft nach jedem Segment
TAKT = 21  # Sekunden zwischen zwei Anfragen (kostenloser Zugang: 3 Anfragen pro Minute)


def sprechen(text, key):
    """Eine Anfrage an die Sprachausgabe, bei Tempolimit (429) warten und neu versuchen."""
    for versuch in range(5):
        try:
            return SA.request_audio(text, key)
        except RuntimeError as e:
            if "429" not in str(e) or versuch == 4:
                raise
            m = re.search(r"retry in (\d+)", str(e))
            time.sleep(min(90, int(m.group(1)) + 5) if m else 50)


def frames(wav_bytes):
    with wave.open(io.BytesIO(wav_bytes)) as w:
        return w.getparams(), w.readframes(w.getnframes())


def main():
    key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not key:
        print("GEMINI_API_KEY fehlt, es wird nichts erzeugt.")
        sys.exit(0)
    items = json.load(open(os.path.join(ROOT, "data", "raetsel.json"), encoding="utf-8"))
    failed = 0
    for q in items:
        base = os.path.join(ROOT, "audio", "raetsel-" + q["id"])
        if os.path.exists(base + ".mp3") and os.path.exists(base + ".json"):
            continue
        try:
            pcm, params, marks, t = b"", None, [], 0.0
            for n, seg in enumerate(q["segmente"]):
                if n:
                    time.sleep(TAKT)
                p, fr = frames(SA.to_wav(sprechen(seg.get("s") or seg["t"], key)))
                params = params or p
                rate, width = params.framerate, params.sampwidth
                dur = len(fr) / (rate * width * params.nchannels)
                pause = float(seg.get("pause", 0)) + GAP
                marks.append([round(t, 2), round(t + dur, 2)])
                pcm += fr + b"\x00" * (int(rate * pause) * width * params.nchannels)
                t += dur + pause
            buf = io.BytesIO()
            with wave.open(buf, "wb") as w:
                w.setparams(params); w.writeframes(pcm)
            subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", "pipe:0", "-ac", "1", "-ar", "24000", "-b:a", "48k", base + ".mp3"],
                           input=buf.getvalue(), check=True)
            json.dump({"dauer": round(t, 2), "marken": marks}, open(base + ".json", "w"))
            print("ok", q["id"], os.path.getsize(base + ".mp3"), "Bytes,", round(t), "Sekunden")
        except Exception as e:  # noqa: BLE001
            failed += 1
            print("FEHLER", q["id"], e, file=sys.stderr)
    sys.exit(1 if failed else 0)


main()
