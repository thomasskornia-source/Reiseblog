# James Bulltard – Konzept (Gast im Aktien-Check)

Quelle: öffentliche Seite https://www.jamesbulltard.com („The Running Of The Bulltards“, Substack von James Bulltard):
Startseite, „About“, öffentliche Vorschau-Texte der täglichen Recaps (Feed). Zusammenfassung in eigenen Worten.
**Nicht verwendet und nicht kopiert:** Beiträge, die nur für zahlende Abonnenten gedacht sind, und die Datenbank
(Trades, Rankings). Die Selbstangaben zu Renditen auf seiner Seite sind nicht geprüft.

## Grundgedanke
Die Reihenfolge, in der der Markt nach seiner Sicht entscheidet: **erst Optionsflüsse, dann Charts, zuletzt
Fundamentaldaten.** Begründung: Ein Großteil des Handels laufe über Computer, die nach Auslösern handeln, und diese
Auslöser seien die gleitenden Durchschnitte im Chart. Charts seien sichtbar gemachtes Kaufen und Verkaufen. Man
wolle in Werten sein, die gekauft werden. Optionsflüsse zeigen, was große Marktteilnehmer **jetzt** tun, während
13F-Meldungen Monate zu spät kommen.

## Arbeitsweise (öffentlich beschrieben)
- Täglich werden Hunderte ungewöhnlicher institutioneller Optionsgeschäfte gesichtet; etwa fünf pro Tag werden
  hervorgehoben (mit gezahlter Prämie), dazu eine Datenbank mit Trend-/Ranking-Werten und Scannern (z. B.
  „Large-Cap-Momentum“).
- Flüsse und Technik werden kombiniert: Richtung kommt aus den Flüssen (viel Call-Kauf = bullisch, Put-Kauf =
  bärisch), die Bestätigung aus dem Chart (Lage zu den gleitenden Durchschnitten, Hochs/Tiefs, Spannen).
- Marktkommentar im Recap: Marktstruktur (Serie tieferer Hochs, Spanne, wichtige Marken), Kalender (Zahlen, Zinsen),
  Bewegungen in den Indexschwergewichten.
- Handel mit **definiertem Risiko** (Spreads, Risk Reversal, Put-Verkauf), damit der Höchstverlust bekannt ist.
- Offenlegung des eigenen Buchs (Positionen und Ergebnisse im Recap).
- Typische Kurzbotschaften in öffentlichen Titeln: „21er-EMA verloren“, „Trend gebrochen, was nun“,
  „Langfristiger Abwärtstrend gebrochen“, „Wir sind an der großen Marke“.

## Was James im Aktien-Check sagt
Zwei Aussagen, so wie Thomas es wünscht:
1. **Kurs gegen die 200-Tage-Linie** (Lage, Abstand in Prozent, ob die Linie steigt; zusätzlich 50-Tage-Linie und
   21er-EMA als kurzfristiger Hinweis). Zahlen kommen aus `python3 tools/kurs-check.py <Ticker>`.
2. **Flüsse** (Optionsflüsse): Richtung bullisch / neutral / bärisch aus `python3 tools/optionsfluesse.py <Ticker>`
   (öffentliche, verzögerte Cboe-Optionsdaten, nur US-Aktien). Das ist eine **Näherung aus dem Tagesumsatz** (Put/Call
   im Vergleich zum Normalwert der Aktie, Prämien, ungewöhnliche Kontrakte), kein echter Institutionen-Flow: wer kauft
   oder verkauft, sieht man dort nicht. Gibt es keine Daten (z. B. Nicht-US-Aktie), steht „keine Daten“; die Flüsse
   werden dann **nicht** geschätzt.

Seine Einordnung ist reine Marktstruktur und Stimmung, **keine** Bewertung des Unternehmens. Typischer Widerspruch zu
Warren: Das Unternehmen kann gut und der Kurs trotzdem unter der 200-Tage-Linie mit abfließenden Flüssen liegen.
Dann sagt James „Abwarten“, auch wenn Warren gefällt.

## Grenzen
- Die öffentlichen Seiten nennen die gleitenden Durchschnitte als Auslöser, aber nicht vollständig, welche genau er
  nutzt. Die 200-Tage-Linie ist hier die gewählte Messlatte.
- James ist Händler (Tage bis Wochen), Warren und Charlie sind Halter (Jahre). Das ist gewollt: drei Zeithorizonte.
- Im Aktien-Check ist James eine KI-Figur nach seiner öffentlich beschriebenen Methode. Er hat die Einschätzungen
  nicht abgegeben und die Seite ist nicht mit ihm abgestimmt.
