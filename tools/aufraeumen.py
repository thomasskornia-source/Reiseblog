#!/usr/bin/env python3
"""Tagesdaten aufräumen: Song-Sprachdateien nach 14 Tagen löschen (die Songseite liest dann mit der Gerätestimme vor),
von den Bayern-Rätseln nur die neuesten 4 behalten (Eintrag und Audio)."""
import datetime as dt, json, os

AUDIO_TAGE = 14
RAETSEL_BEHALTEN = 4
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main():
    heute = dt.date.today()
    songs = json.load(open(os.path.join(ROOT, "data", "songs.json"), encoding="utf-8"))
    datum = {s["id"]: s.get("date") for s in songs if s.get("id")}
    adir = os.path.join(ROOT, "audio")
    # Bayern-Rätsel: nur die neuesten behalten
    rp = os.path.join(ROOT, "data", "raetsel.json")
    behalten = set()
    if os.path.exists(rp):
        rl = sorted(json.load(open(rp, encoding="utf-8")), key=lambda x: x.get("date", ""), reverse=True)
        rest = rl[:RAETSEL_BEHALTEN]
        behalten = {x["id"] for x in rest}
        if len(rl) > len(rest):
            json.dump(rest, open(rp, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
            print("Rätsel entfernt:", [x["id"] for x in rl[RAETSEL_BEHALTEN:]])
    for f in sorted(os.listdir(adir)):
        if f.startswith("raetsel-") and f.endswith((".mp3", ".json")):
            if f[len("raetsel-"):].rsplit(".", 1)[0] not in behalten:
                os.remove(os.path.join(adir, f)); print("gelöscht:", f)
            continue
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
