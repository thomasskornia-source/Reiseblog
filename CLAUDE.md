# Reiseblog – Hinweise für Claude

Überblick über die Aktien-Seite: `aktien.html`, Ablauf der Routine: `AKTIEN-ABLAUF.md`, Wissensbasis: `wissen/`.
Wochenplaner: `wochenplaner.html` (Plan, Einkaufsliste, Vorrat, Reste im Browser), Rezeptdaten `data/wochenplan.json`, erzeugt von
`tools/rezept-index.py` über `.github/workflows/wochenplan.yml`. Auf der Startseite als erste Kachel verlinkt.

Börsenstimmung: `stimmung.html` (Pfeil, Indikatoren, Barometer), Daten `data/koch.json`, erzeugt von `tools/koch-sammeln.py` über
`.github/workflows/koch.yml` (Gemini wertet das neueste YouTube-Video von Markus Koch aus; zweimal täglich, plus von Hand startbar).
Es geht um die Marktlage, nicht um Einzelaktien. Es wird kein Transkript gespeichert, nur die eigene Auswertung mit Quelle. Verlinkt von `aktien.html`.
Quiz: `quiz.html` (Übersicht), `muenchen-quiz.html`, `raetsel.html` (Bayern-Rätsel der Woche zum Anhören, Daten `data/raetsel.json`, Ablauf `QUIZ-ABLAUF.md`,
Audio per `raetsel-audio.yml`). Wöchentlich neu per geplanter Aufgabe, es bleiben 4 Rätsel.
Reiseideen: `reiseideen.html` liest `data/reiseideen.json` (je Link ein Eintrag: titel, ort, art, dauer, preis, kurz, highlights, leistungen, anbieter, url, stand, farben, emoji). Neue Links dort anhängen, Angaben nur von der Anbieterseite, Bilder nicht kopieren. Verlinkt von `reisen.html`. Sterne (1–5) nur lokal im Browser (localStorage), Sortierung nach eigener Bewertung; kein gemeinsames Backend (Thomas, 05.10.2026).
Zeiten (Thomas, 05.10.2026, deutsche Zeit): S&P 500 `markt.yml` Mo–Fr 15:45, 19:00, 21:45 (Tagesstand) und 00:15 (Schluss); Koch `koch.yml` 15:30 und 21:45, dazu 01:00 Nachholversuch. GitHub plant nur in UTC, darum je Zeit eine Sommer- und Winterzeit-Cron, den Job `zeit` überspringt die falsche.
Aufräumen (Thomas, 05.10.2026): Tagesdaten sollen nicht anwachsen. `tools/aufraeumen.py` (läuft in `koch.yml`) löscht Song-Sprachdateien nach 14 Tagen,
`koch-sammeln.py` behält Auswertungen 90 Tage. Neue Tagesdaten bekommen von Anfang an so eine Frist.

## Arbeitsweise (Thomas, 02.10.2026)
- Änderungen am Reiseblog nach eigener Prüfung **direkt zusammenführen** (Entwurf anlegen, prüfen, mit „squash“ auf `main`
  bringen) und kurz auf Deutsch berichten, was online ist. Thomas muss dafür nicht jedes Mal „zusammenführen“ sagen.
- Prüfen heißt: Skripte und Werkzeuge laufen lassen, Seiten bei 390 und 1400 px ansehen (keine Seitenverbreiterung,
  keine JS-Fehler), JSON-Dateien auf Gültigkeit prüfen.
- **Vorher fragen**, wie bisher: das Anstoßen oder Ändern der Routinen und des Apps Scripts, Dinge, die Geld kosten oder
  Zugangsdaten betreffen, Inhalte, die eine echte Person namentlich darstellen oder in deren Namen sprechen, und alles,
  was Seiten oder Daten löscht.
- Keine Inhalte aus Bezahlbeiträgen Dritter kopieren; Mitschriften und Texte Dritter nicht ins Repo legen, nur Fundstellen
  und kurze Zitate mit Quelle.
