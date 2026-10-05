# Indikatoren: wöchentliche Rückmeldung „Selbst abrufbar?“

Ziel (Thomas, 05.10.2026): Markus Kochs Indikatoren lernen, und Schritt für Schritt die Indikatoren, die sich über mehrere Tage wiederholen,
**selbst aus frei zugänglichen Quellen** abrufen, damit man seine Videos nicht mehr anhören muss.

## Wie die Indikatoren wachsen (läuft automatisch)
- `tools/koch-sammeln.py` wertet jedes neue Video aus und bekommt dabei die bisherigen Indikatornamen mit, damit Wiederholungen gleich benannt werden.
- `tools/koch-katalog.py` zählt je Kategorie die **verschiedenen Tage**: 1 = neu, 2 = beobachtet, ab 3 = bestätigt. Ergebnis `data/koch-indikatoren.json`
  (angezeigt auf `stimmung.html` unter „Seine festen Indikatoren“).

## Wöchentliche Aufgabe (Samstag früh): Rückmeldung schreiben
1. Repo `thomasskornia-source/Reiseblog` mit Schreibrecht verfügbar machen (`add_repo`, `access: push`) und flach klonen.
2. `data/koch-indikatoren.json` und `data/koch.json` lesen. Zeitraum der Woche und Anzahl der Auswertungen nennen. Gibt es keine Daten dieser Woche, nur das
   melden und nichts schreiben.
3. Für jeden Indikator mit Status **bestätigt** oder **beobachtet** (neue nur kurz erwähnen) prüfen, ob es eine **frei zugängliche, automatisch abrufbare**
   Quelle gibt, ohne Anmeldung und ohne Kosten. Mit WebSearch/WebFetch nachsehen, nichts aus dem Gedächtnis behaupten. Beispiele für Quellenarten:
   Yahoo Finance (Kurse, Ölpreis, Renditen, VIX, Dollar, Sektoren-ETFs; wird im Repo bereits von `tools/trend.py` genutzt), FRED (Zinsen, Renditen, Inflation,
   Arbeitsmarkt), BLS/BEA/EIA, US-Finanzministerium, Cboe, AAII, offizielle Kalender. Für jede Quelle sagen: was genau abrufbar ist, wie oft sie sich ändert,
   ob ein Schlüssel nötig ist, ob sie vom GitHub-Runner erreichbar sein dürfte.
4. Je Indikator bewerten: `machbar` = `ja` (frei und automatisch), `teilweise` (nur Teil oder mit Aufwand/Verzögerung), `nein` (nur über Kochs Einschätzung,
   z. B. Positionierung, Stimmung, Politik). Immer **ehrlich** begründen, nichts erfinden, Unsicheres als unsicher kennzeichnen.
5. `data/koch-feedback.json` schreiben (Schema unten) und committen: Nachricht „Indikatoren: Rückmeldung KW <nn>“, auf `main` pushen.
6. Push-Benachrichtigung senden: eine Zeile, z. B. „Rückmeldung zu den Indikatoren ist da: x von y selbst abrufbar“.
7. Im Bericht in drei Sätzen sagen: welche Indikatoren sich als fest erwiesen haben, was sofort selbst abrufbar wäre, und **ein** konkreter Vorschlag für den
   nächsten Schritt (z. B. „Ölpreis, 10-jährige Rendite und VIX täglich per Yahoo abrufen und als eigene Pfeile anzeigen“). Nichts davon ohne Rückfrage
   einbauen.

```json
{
  "stand": "10.10.2026",
  "zusammenfassung": "Zwei bis drei Sätze: Woche, Anzahl Auswertungen, Fazit.",
  "indikatoren": [
    {"name": "Ölpreis", "kategorie": "Öl & Rohstoffe", "machbar": "ja", "quelle": "Yahoo Finance (CL=F)", "url": "https://finance.yahoo.com/quote/CL=F", "hinweis": "Tageskurse, kein Schlüssel nötig."}
  ]
}
```

Regeln: keine Inhalte aus Bezahlquellen kopieren, keine Anlageberatung, nur Quellen mit Link nennen, die man wirklich geprüft hat.
