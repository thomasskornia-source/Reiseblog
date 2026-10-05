# Reiseblog – Hinweise für Claude

Überblick über die Aktien-Seite: `aktien.html`, Ablauf der Routine: `AKTIEN-ABLAUF.md`, Wissensbasis: `wissen/`.
Wochenplaner: `wochenplaner.html` (Plan, Einkaufsliste, Vorrat, Reste im Browser), Rezeptdaten `data/wochenplan.json`, erzeugt von
`tools/rezept-index.py` über `.github/workflows/wochenplan.yml`. Auf der Startseite als erste Kachel verlinkt.

Börsenstimmung: `stimmung.html` (Pfeil, Indikatoren, Barometer), Daten `data/koch.json`, erzeugt von `tools/koch-sammeln.py` über
`.github/workflows/koch.yml` (Gemini wertet das neueste YouTube-Video von Markus Koch aus; zweimal täglich, plus von Hand startbar).
Es wird kein Transkript gespeichert, nur die eigene Auswertung mit Quelle. Verlinkt von `aktien.html`.

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
