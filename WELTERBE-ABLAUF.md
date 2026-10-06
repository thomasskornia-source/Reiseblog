# UNESCO-Welterbe der Woche – Ablauf

Jeden Mittwoch (zwei Tage nach dem Bayern-Rätsel) kommt **ein** neues UNESCO-Welterbe dazu: Streifen auf `index.html`, Seite `welterbe.html`,
Daten `data/welterbe.json`. Es bleiben die 12 neuesten (`tools/aufraeumen.py`).

## Schritte
1. Ist der neueste Eintrag in `data/welterbe.json` jünger als 6 Tage (Datum Europa/Berlin), **nichts tun** und das melden.
2. Ein UNESCO-Welterbe wählen, das noch nicht in `data/welterbe.json` steht. Abwechslung: Kultur und Natur, verschiedene Kontinente,
   gelegentlich Deutschland/Bayern/Alpenraum; bekannt oder überraschend. Keine heiklen Themen als Schwerpunkt (Krieg, Gewalt).
3. Fakten von whc.unesco.org (WebFetch/WebSearch) und Wikipedia prüfen, **nur Belegtes**, Zahlen und Namen genau.
4. Auf Deutsch in **eigenen Worten**, locker, gut vorlesbar, 220–300 Wörter, drei bis vier Absätze (Ort/Eindruck, Geschichte, Besonderes,
   Welterbe seit wann und warum). Keine wörtlichen Übernahmen.
5. Eintrag anhängen:
   `{"id":"slug","date":"JJJJ-MM-TT","titel":"…","ort":"Ort, Region","land":"…","seit":1983,"kurz":"ein Satz","text":"Absatz\n\nAbsatz","sprech":"gesprochene Fassung","quelle":{"titel":"Wikipedia: …","url":"…"}}`
   `sprech` = Titel + Text mit **ausgeschriebenen Zahlen und Jahren** (z. B. „siebzehnhundertvierzig“), ohne Absatzmarken. Titelansage am Anfang.
   `id` nur Kleinbuchstaben, Ziffern, Bindestriche. JSON mit `python3 -m json.tool` prüfen.
   **Bild (optional, aber gewünscht):** ein Foto von Wikimedia Commons (Datei-Seite per WebSearch/WebFetch lesen). Nur Dateien mit freier Lizenz (CC BY, CC BY-SA, CC0, Public Domain, GFDL), Lizenz und Autor **von der Dateiseite übernehmen**, nichts raten; eingebunden wird nur per Link (nichts ins Repo kopieren):
   `"bild":{"datei":"Dateiname.jpg","autor":"…","lizenz":"CC BY-SA 4.0","seite":"https://commons.wikimedia.org/wiki/File:Dateiname.jpg","alt":"Bildbeschreibung"}`
   Kein sicheres freies Foto gefunden: Feld weglassen.
6. `git pull --rebase origin main`, auf `main` pushen („Welterbe der Woche: <Titel>“, mit Co-Authored-By/Claude-Session-Zeilen).
   Die Sprachdatei erzeugt danach `welterbe-audio.yml` (Gemini, 1 Anfrage), ohne Datei liest die Seite mit der Gerätestimme.
7. Kurz berichten: welches Welterbe, ein Satz dazu.
