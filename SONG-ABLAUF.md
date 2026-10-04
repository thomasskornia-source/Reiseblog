# Song des Tages – Ablauf

Jeden Morgen kommt genau **ein** neuer Song dazu. Die Songliste (537 Titel aus Thomas' Spotify-Playlist
„Won't forget these days“) liegt **nicht** im Repo, sondern in Google Drive: Datei **„Song des Tages – Songliste.csv“**
(Spalten: Titel, Interpret, Spotify-Jahr, Spotify-ID). Auf der Webseite stehen nur die bereits veröffentlichten Songs,
in `data/songs.json`.

## Schritte

1. Repo `thomasskornia-source/Reiseblog` mit Schreibrecht verfügbar machen (`add_repo`, `access: push`) und flach klonen.
2. `data/songs.json` lesen. Gibt es schon einen Eintrag mit dem heutigen Datum (Europa/Berlin, `YYYY-MM-DD`)? Dann **nichts tun** und das kurz melden.
3. Die Songliste aus Google Drive lesen (Suche: Titel enthält „Songliste“).
4. **Zufälligen** Song wählen, der noch nicht veröffentlicht ist (Vergleich über Spotify-ID und über bereinigten Titel + Interpret, ohne Zusätze wie „Remastered“, „Live“, „Mix“). Zufall mit `python3 random.choice`, nicht „der Reihe nach“. Keine doppelten Songs, auch nicht in anderer Version.
5. Titel bereinigen (ohne „- 2011 Remaster“, „- Live …“ usw.), ursprüngliches Erscheinungsjahr des Songs recherchieren (nicht das Jahr der Neuauflage).
6. Per WebSearch/WebFetch recherchieren: Wer hat den Song geschrieben, wie und wann ist er entstanden, worum geht es, was ist die verbreitete Deutung. Nur belegte Fakten verwenden. Was nicht belegt ist, weglassen, nichts erfinden.
7. Auf Deutsch schreiben, in eigenen Worten, locker und verständlich, so dass es gut vorgelesen klingt:
   - `herkunft`: Woher kommt der Song? (ca. 50–80 Wörter)
   - `bedeutung`: Was bedeutet er? (ca. 50–80 Wörter)
   - `fun`: optional, ein kurzes belegtes Detail (ein bis zwei Sätze). Weglassen, wenn nichts Gutes da ist.
   - **Keine Liedtexte** und keine Zitate aus Texten oder Artikeln. Keine wörtlichen Übernahmen aus Quellen.
   - Bei heiklen Themen (Gewalt, Sucht, Suizid, sexualisierte Gewalt, politische Provokation) sachlich und respektvoll bleiben, keine Details zu Methoden, keine Verharmlosung.
8. Spotify-ID prüfen: `https://open.spotify.com/track/<ID>` per WebFetch laden. Passt der Titel, Feld `spotify` setzen. Passt er nicht oder ist die Seite nicht lesbar, Feld `spotify` weglassen (die Seite nutzt dann einen Spotify-Suchlink).
9. Neuen Eintrag an `data/songs.json` anhängen (nichts anderes ändern):
   ```json
   {"id": "kurzer-slug", "date": "YYYY-MM-DD", "title": "…", "artist": "…", "year": 1984,
    "spotify": "ID", "herkunft": "…", "bedeutung": "…", "fun": "…"}
   ```
   JSON auf Gültigkeit prüfen (`python3 -m json.tool`). `id` nur Kleinbuchstaben, Ziffern, Bindestriche, eindeutig.
10. `git fetch origin main`, auf `main` committen und pushen (Commit-Nachricht: „Song des Tages: <Titel> – <Interpret>“, mit den üblichen Co-Authored-By/Claude-Session-Zeilen).
11. Nach dem Push kurz berichten: welcher Song, ein Satz zur Geschichte. Der Song erscheint nach etwa ein bis zwei Minuten auf der Startseite.

## Audio

Die Audiodatei zum Vorlesen (`audio/<id>.mp3`) erzeugt **automatisch** der GitHub-Workflow `song-audio.yml` (Skript `tools/song-audio.py`, Gemini-Sprachausgabe, Schlüssel als GitHub-Secret `GEMINI_API_KEY`), sobald `data/songs.json` auf `main` geändert wird. Dafür ist in der täglichen Aufgabe nichts zu tun. Fehlt die Datei, liest die Seite mit der Stimme des Geräts vor.

Bei Fehlern (kein Zugriff auf Drive, Push scheitert): nichts halb Fertiges hinterlassen, den Fehler klar melden.
