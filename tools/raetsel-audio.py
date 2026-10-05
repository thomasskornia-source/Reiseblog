#!/usr/bin/env python3
"""Erzeugt zu jedem Bayern-Rätsel in data/raetsel.json audio/raetsel-<id>.mp3 und audio/raetsel-<id>.json (Zeitmarken).

Je Frage wird ein Block aus Segmenten in einer Anfrage gesprochen (Gemini-Sprachausgabe, wie tools/song-audio.py). Nach Fragen wird eine Denkpause
(Segmentfeld "pause", Sekunden) eingefügt. Gesprochen wird "s" (Zahlen ausgeschrieben), sonst "t". Braucht GEMINI_API_KEY und ffmpeg. Vorhandene Dateien werden übersprungen.
"""
import importlib.util, io, json, os, re, subprocess, sys, time, wave

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
spec = importlib.util.spec_from_file_location("song_audio", os.path.join(ROOT, "tools", "song-audio.py"))
SA = importlib.util.module_from_spec(spec); spec.loader.exec_module(SA)
GAP = 0.7  # Sekunden Luft nach jedem Segment
TAKT = 21  # Sekunden zwischen zwei Anfragen (kostenloser Zugang: 3 Anfragen pro Minute)


def tageslimit(e):
    return "per day" in str(e) or "PerDay" in str(e)


def edge_wav(text):
    """Ersatzstimme: Microsoft Seraphina (edge-tts, kein Schlüssel nötig) als WAV (24 kHz, mono)."""
    import asyncio, edge_tts, tempfile
    with tempfile.TemporaryDirectory() as d:
        mp3 = os.path.join(d, "x.mp3")
        asyncio.run(edge_tts.Communicate(text, "de-DE-SeraphinaMultilingualNeural", rate="-4%").save(mp3))
        return subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", mp3, "-ac", "1", "-ar", "24000", "-f", "wav", "pipe:1"],
                              check=True, capture_output=True).stdout


def sprechen(text, key):
    """Eine Anfrage an die Sprachausgabe, bei Tempolimit (429) warten und neu versuchen."""
    for versuch in range(5):
        try:
            return SA.request_audio(text, key)
        except RuntimeError as e:
            if "429" not in str(e) or versuch == 4 or tageslimit(e):
                raise
            m = re.search(r"retry in (\d+)", str(e))
            time.sleep(min(90, int(m.group(1)) + 5) if m else 50)


def frames(wav_bytes):
    with wave.open(io.BytesIO(wav_bytes)) as w:
        return w.getparams(), w.readframes(w.getnframes())


def erzeugen(q, base, stimme, key):
    # Je Frage ein Block (Geschichte, Antwort, nächste Geschichte, Frage), danach die Denkpause.
    # Gemini: nur 10 Sprachanfragen pro Tag und 3 pro Minute im kostenlosen Zugang.
    bloecke, cur = [], []
    for i, seg in enumerate(q["segmente"]):
        cur.append(i)
        if seg["k"] == "f" or i == len(q["segmente"]) - 1:
            bloecke.append(cur); cur = []
    pcm, params, marks, t = b"", None, [None] * len(q["segmente"]), 0.0
    for n, idx in enumerate(bloecke):
        texte = [q["segmente"][i].get("s") or q["segmente"][i]["t"] for i in idx]
        if stimme == "gemini":
            if n:
                time.sleep(TAKT)
            wav = SA.to_wav(sprechen(" ".join(texte), key))
        else:
            wav = edge_wav(" ".join(texte))
        p, fr = frames(wav)
        params = params or p
        rate, width = params.framerate, params.sampwidth
        dur = len(fr) / (rate * width * params.nchannels)
        pause = float(q["segmente"][idx[-1]].get("pause", 0)) + GAP
        total, c = sum(len(x) for x in texte) or 1, 0   # Zeit je Segment nach Zeichenzahl verteilen
        for i, x in zip(idx, texte):
            marks[i] = [round(t + dur * c / total, 2), round(t + dur * (c + len(x)) / total, 2)]
            c += len(x)
        pcm += fr + b"\x00" * (int(rate * pause) * width * params.nchannels)
        t += dur + pause
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setparams(params); w.writeframes(pcm)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", "pipe:0", "-ac", "1", "-ar", "24000", "-b:a", "48k", base + ".mp3"],
                   input=buf.getvalue(), check=True)
    json.dump({"dauer": round(t, 2), "marken": marks, "stimme": "edge" if stimme == "edge" else "gemini"}, open(base + ".json", "w"))
    print("ok", q["id"], stimme, os.path.getsize(base + ".mp3"), "Bytes,", round(t), "Sekunden")


def main():
    key = os.environ.get("GEMINI_API_KEY", "").strip()
    gemini_ok = bool(key) and os.environ.get("NUR_ERSATZ") != "1"   # wird falsch, sobald das Tageslimit erreicht ist
    items = json.load(open(os.path.join(ROOT, "data", "raetsel.json"), encoding="utf-8"))
    failed = 0
    for q in items:
        base = os.path.join(ROOT, "audio", "raetsel-" + q["id"])
        if os.path.exists(base + ".mp3") and os.path.exists(base + ".json"):
            try:
                ersatz = json.load(open(base + ".json")).get("stimme") == "edge"
            except Exception:  # noqa: BLE001
                ersatz = False
            if not (ersatz and gemini_ok):
                continue   # fertig; die Ersatzstimme wird durch Googles Stimme ersetzt, sobald das Limit es zulässt
            vorhanden = True
        else:
            vorhanden = False
        try:
            if gemini_ok:
                try:
                    erzeugen(q, base, "gemini", key)
                    continue
                except Exception as e:  # noqa: BLE001
                    print("Gemini nicht möglich:", str(e)[:200], file=sys.stderr)
                    gemini_ok = False
                    if vorhanden:
                        continue   # Ersatzdatei bleibt bestehen
            erzeugen(q, base, "edge", key)
        except Exception as e:  # noqa: BLE001
            failed += 1
            print("FEHLER", q["id"], e, file=sys.stderr)
    sys.exit(1 if failed else 0)


main()
