#!/usr/bin/env python3
"""Trendbruch-Meldung: legt ein GitHub-Issue an (-> Push in der GitHub-App), wenn die Warnstufe steigt.
Stufen wie in nav.js: 0 keine, 1 unter 21er, 2 plus ein Zeichen, 3 plus zwei. Zustand: data/warnstufe.json."""
import json, os, subprocess
m = json.load(open("data/markt.json"))
z = []
if m["ma8"] < m["ma21"]: z.append("8er unter 21er")
w = m.get("woche") or {}
if w.get("macd_ueber_signal") is False: z.append("Wochen-MACD unter Signallinie")
if w.get("ueber_ema8") is False: z.append("unter dem 8-Wochen-EMA")
if m["kurs"] < m["ma50"]: z.append("unter der 50er")
stufe = 0 if m["kurs"] >= m["ma21"] else (3 if len(z) >= 2 else 2 if len(z) == 1 else 1)
f = "data/warnstufe.json"
alt = json.load(open(f)).get("stufe", 0) if os.path.exists(f) else 0
if stufe > alt:
    kopf = ["", "Hinweis", "Warnung", "Alarm"][stufe]
    text = f"S&P 500 unter der 21-Tage-Linie (Stand {m['stand']}, Kurs {m['kurs']}, 21er {m['ma21']}).\nZeichen: {', '.join(z) or 'keine weiteren'}.\nKann auch ein falscher Bruch sein. Keine Anlageberatung. Details: aktien.html"
    if os.environ.get("GITHUB_REPOSITORY") and os.environ.get("GH_TOKEN"):
        subprocess.run(["gh", "api", f"repos/{os.environ['GITHUB_REPOSITORY']}/issues", "-f", f"title=Trendbruch S&P 500: {kopf} (Stufe {stufe})", "-f", f"body={text}"], check=False)
    print("Meldung:", kopf, stufe)
if stufe != alt:
    json.dump({"stufe": stufe, "stand": m["stand"]}, open(f, "w"))
