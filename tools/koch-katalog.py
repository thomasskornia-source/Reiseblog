#!/usr/bin/env python3
"""Baut aus data/koch.json den Indikator-Katalog data/koch-indikatoren.json.

Je Kategorie (Arbeitsmarkt, Zinsen, Öl …) wird gezählt, an wie vielen verschiedenen Tagen Markus Koch sie nutzt.
Wiederholt sich ein Indikator über mehrere Tage, gilt er als gesichert: 1 Tag = neu, 2 Tage = beobachtet, ab 3 Tagen = bestätigt.
Der Katalog behält die Tageswerte auch dann, wenn koch.json nach 90 Tagen aufräumt (höchstens 180 Tage je Kategorie).
Er ist reine Auswertung (keine Abrufe, keine Kosten) und wird nur geschrieben, wenn sich der Inhalt ändert.
"""
import json, os, collections

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KOCH = os.path.join(ROOT, "data", "koch.json")
OUT = os.path.join(ROOT, "data", "koch-indikatoren.json")
SCHWELLE = {"bestaetigt": 3, "beobachtet": 2}
MAX_TAGE = 180
PF = {"hoch": 1, "runter": -1}


def main():
    if not os.path.exists(KOCH):
        return
    koch = json.load(open(KOCH, encoding="utf-8"))
    alt = json.load(open(OUT, encoding="utf-8")) if os.path.exists(OUT) else {}
    # tage[kategorie][datum] = {"p": Summe der Pfeile, "namen": [...], "rolle": ...}
    tage = {k["kategorie"]: dict(k.get("tage", {})) for k in alt.get("kategorien", [])}
    neu = collections.defaultdict(lambda: collections.defaultdict(lambda: {"p": 0, "namen": [], "rolle": ""}))
    for b in sorted(koch.get("beitraege", []), key=lambda x: x.get("zeit", "")):
        for i in b.get("indikatoren", []):
            e = neu[i.get("kategorie", "Sonstiges")][b["datum"]]
            e["p"] += PF.get(i.get("pfeil"), 0)
            if i.get("name") and i["name"] not in e["namen"]:
                e["namen"].append(i["name"])
            e["rolle"] = i.get("rolle") or e["rolle"]
    for kat, tg in neu.items():
        for d, e in tg.items():
            tage.setdefault(kat, {})[d] = e
    kategorien = []
    for kat, tg in tage.items():
        tg = dict(sorted(tg.items())[-MAX_TAGE:])
        n = len(tg)
        namen = collections.Counter(x for e in tg.values() for x in e["namen"])
        letzter = max(tg)
        status = "bestaetigt" if n >= SCHWELLE["bestaetigt"] else "beobachtet" if n >= SCHWELLE["beobachtet"] else "neu"
        kategorien.append({
            "kategorie": kat, "status": status, "tage_anzahl": n, "erstmals": min(tg), "zuletzt": letzter,
            "name": namen.most_common(1)[0][0] if namen else kat,
            "namen": [x for x, _ in namen.most_common(6)],
            "rolle": tg[letzter]["rolle"],
            "tage": tg,
        })
    rang = {"bestaetigt": 0, "beobachtet": 1, "neu": 2}
    kategorien.sort(key=lambda k: (rang[k["status"]], -k["tage_anzahl"], k["kategorie"]))
    stand = max((b["datum"] for b in koch.get("beitraege", [])), default=alt.get("stand", ""))
    db = {"stand": stand, "schwellen": {"bestaetigt": SCHWELLE["bestaetigt"], "beobachtet": SCHWELLE["beobachtet"]}, "kategorien": kategorien}
    neu_text = json.dumps(db, ensure_ascii=False, indent=1)
    if os.path.exists(OUT) and open(OUT, encoding="utf-8").read() == neu_text:
        print("Katalog unverändert"); return
    open(OUT, "w", encoding="utf-8").write(neu_text)
    print("Katalog:", ", ".join("%s %s (%d)" % (k["kategorie"], k["status"], k["tage_anzahl"]) for k in kategorien))


main()
