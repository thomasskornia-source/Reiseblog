# Bayern-Rätsel der Woche – Ablauf

Jeden Montag kommt **ein** neues Rätsel dazu: eine kurze Geschichte zu einem Wikipedia-Artikel über Bayern, am liebsten Oberbayern,
mit drei Fragen und Denkpausen zum Anhören (`raetsel.html`, Übersicht `quiz.html`). Einträge stehen in `data/raetsel.json`.
Die bisher benutzten Artikel stehen in `data/raetsel-verwendet.json` (nur Titel, wird nicht aufgeräumt).

## Schritte

1. Repo `thomasskornia-source/Reiseblog` mit Schreibrecht verfügbar machen (`add_repo`, `access: push`) und flach klonen.
2. `data/raetsel.json` lesen. Ist der neueste Eintrag jünger als 6 Tage (Datum Europa/Berlin), **nichts tun** und das kurz melden.
3. Einen **interessanten Wikipedia-Artikel** zu Bayern wählen, bevorzugt Oberbayern (Orte, Natur, Technik, Geschichte, Brauchtum,
   Persönlichkeiten). Noch nicht in `data/raetsel-verwendet.json`. Kein Artikel zu heiklen Themen (Gewalt, Verbrechen, NS-Zeit,
   Politik). Der Artikel muss genug Stoff für drei gute Fragen haben, die man **aus dem Gehörten** erraten oder schätzen kann.
4. Den Artikel lesen (WebFetch; ist Wikipedia nicht abrufbar, eine Spiegelseite wie austria-forum.org/af/AustriaWiki/<Titel>).
   **Nur belegte Fakten** verwenden, nichts erfinden. Zahlen und Namen genau übernehmen.
5. Auf Deutsch in **eigenen Worten** schreiben, locker, gut vorlesbar, kurze Sätze. Keine wörtlichen Übernahmen. Ziel: etwa 330–420
   gesprochene Wörter (2,5–3 Minuten ohne Pausen).
6. Aufbau der `segmente` (Reihenfolge fest, jedes Segment wird einzeln gesprochen):
   - `t` Titelansage: „Das Bayern-Rätsel der Woche: <Titel>. <Untertitel>.“
   - `t` Einstieg in die Geschichte (Szene, worum geht es)
   - `f` **Frage 1** („Erste Frage: …? Denk kurz nach.“), Feld `pause`: 8
   - `a` Antwort 1 („Die Antwort: …“) mit kurzer Erklärung
   - `t` Weiter in der Geschichte, `f` Frage 2 (`pause`: 8), `a` Antwort 2
   - `t` Weiter, `f` Frage 3 (`pause`: 8), `a` Antwort 3
   - `t` Schluss: Was ist heute davon zu sehen oder zu erleben? Endet mit „Das war das Bayern-Rätsel der Woche. Bis nächsten Montag!“
   Fragen aus dem Kontext: schätzen (Zahlen mit drei Antwortmöglichkeiten), erraten („Was glaubst du, warum …?“). Keine Frage, die nur mit
   Vorwissen zu beantworten ist.
   **Zahlen:** `t` ist der Anzeigetext (mit Ziffern). Enthält ein Segment Zahlen, steht zusätzlich `s` mit der gesprochenen Fassung
   (Zahlen und Jahre ausgeschrieben, z. B. „sechzehnhundertsiebzehn“).
7. Neuen Eintrag **vorn oder hinten** an `data/raetsel.json` anhängen (nichts anderes ändern):
   ```json
   {"id": "kurzer-slug", "date": "YYYY-MM-DD", "titel": "…", "teaser": "ein Satz", "ort": "Orte, kommagetrennt",
    "quelle": {"titel": "Wikipedia: <Artikel>", "url": "https://de.wikipedia.org/wiki/<Artikel>"},
    "segmente": [{"k": "t", "t": "…"}, {"k": "f", "t": "…", "pause": 8}, {"k": "a", "t": "…", "s": "…"}]}
   ```
   Den Artikeltitel zusätzlich an `data/raetsel-verwendet.json` anhängen. Beide JSON-Dateien mit `python3 -m json.tool` prüfen.
   `id` nur Kleinbuchstaben, Ziffern, Bindestriche, eindeutig. Genau 11 Segmente (Titel, Einstieg, 3 × Frage/Antwort mit je einem
   `t` dazwischen, Schluss) sind die Vorlage; Abweichungen nur mit gutem Grund. Die Audio-Marken je Segment müssen zur Segmentzahl passen.
8. `git fetch origin main`, auf `main` committen und pushen (Nachricht „Bayern-Rätsel: <Titel>“, mit den üblichen
   Co-Authored-By/Claude-Session-Zeilen).
9. Kurz berichten: welches Thema, ein Satz dazu. Das Rätsel erscheint nach etwa ein bis zwei Minuten, die Sprachdatei etwa fünf bis zehn Minuten später.

## Audio

`audio/raetsel-<id>.mp3` und `audio/raetsel-<id>.json` (Zeitmarken) erzeugt **automatisch** der Workflow `raetsel-audio.yml`
(Skript `tools/raetsel-audio.py`, Gemini-Stimme, Denkpausen eingebaut), sobald `data/raetsel.json` auf `main` geändert wird.
Fehlt die Datei, liest die Seite mit der Gerätestimme vor.
Der kostenlose Gemini-Zugang erlaubt nur **10 Sprachanfragen pro Tag** (und 3 pro Minute). Das Skript braucht darum pro Rätsel nur 4 Anfragen
(ein Block je Frage) und wartet zwischen den Anfragen. Ist das Tageslimit erreicht, holt ein täglicher Lauf des Workflows (00:20 und 06:20 UTC)
die Datei nach. Die tägliche Song-Aufgabe braucht 1 Anfrage pro Tag.

## Aufräumen

Es bleiben die **4 neuesten** Rätsel (Eintrag und Audio). `tools/aufraeumen.py` entfernt ältere automatisch.

Bei Fehlern: nichts halb Fertiges hinterlassen, den Fehler klar melden.
