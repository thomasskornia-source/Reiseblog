#!/usr/bin/env python3
"""Einmaliger Stimmen-Vergleich: spricht den Anfang des aktuellen Bayern-Rätsels mit mehreren kostenlosen Stimmen (ohne Schlüssel)
und legt die Proben als audio/probe-<name>.mp3 ab. Nicht für den Dauerbetrieb."""
import asyncio, json, os, subprocess, sys, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
q = json.load(open(os.path.join(ROOT, "data", "raetsel.json"), encoding="utf-8"))[-1]
TEXT = " ".join((s.get("s") or s["t"]) for s in q["segmente"][:3])
OUT = os.path.join(ROOT, "audio")
os.makedirs(OUT, exist_ok=True)
log = []


async def edge(name, voice):
    import edge_tts
    pfad = os.path.join(OUT, f"probe-{name}.mp3")
    try:
        await edge_tts.Communicate(TEXT, voice, rate="-4%").save(pfad)
        log.append(f"ok {name} {os.path.getsize(pfad)} Bytes")
    except Exception as e:  # noqa: BLE001
        log.append(f"FEHLER {name}: {type(e).__name__} {str(e)[:200]}")


def piper(name, sprecher, qualitaet):
    try:
        datei = f"de_DE-{sprecher}-{qualitaet}"
        base = f"https://huggingface.co/rhasspy/piper-voices/resolve/main/de/de_DE/{sprecher}/{qualitaet}/{datei}"
        onnx = f"/tmp/{name}.onnx"
        urllib.request.urlretrieve(base + ".onnx", onnx)
        urllib.request.urlretrieve(base + ".onnx.json", onnx + ".json")
        wav = f"/tmp/{name}.wav"
        subprocess.run([sys.executable, "-m", "piper", "-m", onnx, "-f", wav], input=TEXT.encode(), check=True, capture_output=True)
        pfad = os.path.join(OUT, f"probe-{name}.mp3")
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", wav, "-ac", "1", "-b:a", "64k", pfad], check=True)
        log.append(f"ok {name} {os.path.getsize(pfad)} Bytes")
    except Exception as e:  # noqa: BLE001
        log.append(f"FEHLER {name}: {type(e).__name__} {str(e)[:200]}")


async def main():
    for name, voice in (("edge-katja", "de-DE-KatjaNeural"), ("edge-seraphina", "de-DE-SeraphinaMultilingualNeural"),
                        ("edge-conrad", "de-DE-ConradNeural"), ("edge-amala", "de-DE-AmalaNeural")):
        await edge(name, voice)
    piper("piper-thorsten", "thorsten", "medium")


asyncio.run(main())
open(os.path.join(ROOT, "audio", "last-probe.log"), "w").write("\n".join(log) + "\n")
print("\n".join(log))
