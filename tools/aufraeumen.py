#!/usr/bin/env python3
"""Tagesdaten aufräumen: Song-Sprachdateien nach 14 Tagen löschen (die Songseite liest dann mit der Gerätestimme vor)."""
import datetime as dt, json, os

AUDIO_TAGE = 14
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main():
    heute = dt.date.today()
    songs = json.load(open(os.path.join(ROOT, "data", "songs.json"), encoding="utf-8"))
    datum = {s["id"]: s.get("date") for s in songs if s.get("id")}
    adir = os.path.join(ROOT, "audio")
    for f in sorted(os.listdir(adir)):
        if not f.endswith(".mp3"):
            continue
        d = datum.get(f[:-4])
        try:
            alt = (heute - dt.date.fromisoformat(d)).days if d else AUDIO_TAGE + 1  # ohne Songeintrag: verwaist
        except ValueError:
            continue
        if alt > AUDIO_TAGE:
            os.remove(os.path.join(adir, f))
            print("gelöscht:", f, f"({alt} Tage alt)")


main()
