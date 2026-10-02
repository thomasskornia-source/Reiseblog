# James Bulltard – Konzept (Gast im Aktien-Check)

Quelle: öffentliche Seite https://www.jamesbulltard.com („The Running Of The Bulltards“, Substack von James Bulltard):
Startseite, „About“, öffentliche Vorschau-Texte der täglichen Recaps (Feed). Zusammenfassung in eigenen Worten.
**Nicht verwendet und nicht kopiert:** Beiträge, die nur für zahlende Abonnenten gedacht sind, und die Datenbank
(Trades, Rankings). Die Selbstangaben zu Renditen auf seiner Seite sind nicht geprüft.

## Grundgedanke
Die Reihenfolge, in der der Markt nach seiner Sicht entscheidet: **erst Option Flows, dann Charts, zuletzt
Fundamentaldaten.** Begründung: Ein Großteil des Handels laufe über Computer, die nach Auslösern handeln, und diese
Auslöser seien die gleitenden Durchschnitte im Chart. Charts seien sichtbar gemachtes Kaufen und Verkaufen. Man
wolle in Werten sein, die gekauft werden. Option Flows zeigen, was große Marktteilnehmer **jetzt** tun, während
13F-Meldungen Monate zu spät kommen.

## Arbeitsweise (öffentlich beschrieben)
- Täglich werden Hunderte ungewöhnlicher institutioneller Optionsgeschäfte gesichtet; etwa fünf pro Tag werden
  hervorgehoben (mit gezahlter Prämie), dazu eine Datenbank mit Trend-/Ranking-Werten und Scannern (z. B.
  „Large-Cap-Momentum“).
- Option Flows und Technik werden kombiniert: Richtung kommt aus den Option Flows (viel Call-Kauf = bullisch, Put-Kauf =
  bärisch), die Bestätigung aus dem Chart (Lage zu den gleitenden Durchschnitten, Hochs/Tiefs, Spannen).
- Marktkommentar im Recap: Marktstruktur (Serie tieferer Hochs, Spanne, wichtige Marken), Kalender (Zahlen, Zinsen),
  Bewegungen in den Indexschwergewichten.
- Handel mit **definiertem Risiko** (Spreads, Risk Reversal, Put-Verkauf), damit der Höchstverlust bekannt ist.
- Offenlegung des eigenen Buchs (Positionen und Ergebnisse im Recap).
- Typische Kurzbotschaften in öffentlichen Titeln: „21er-EMA verloren“, „Trend gebrochen, was nun“,
  „Langfristiger Abwärtstrend gebrochen“, „Wir sind an der großen Marke“.

## Was James im Aktien-Check sagt
1. **Trend nach den Regeln von Thomas, angelehnt an James** (`tools/trend.py`): Kurs gegen die Linien 8, 21 (EMA) und
   50, 200 (Durchschnitt). Ergebnis ist eine Ampel: **Up** (über 8, 21 und 50), **Medium** (der Markt weiß nicht wohin:
   zwischen 21 und 50, Rücksetzer unter 8 oder über 8/21 aber unter 50), **Down** (unter 21 und 50, oder unter 200).
   Dazu ein Kerzenchart mit Volumen und den vier Linien (ohne RSI und MACD).
2. **Marktstimmung:** Dieselbe Logik auf den S&P 500, nur als Indikator Up / Medium / Down (kein Chart), täglich
   aktualisiert (`tools/markt.py`, GitHub-Aktion). James setzt die Aktie ins Verhältnis zum Markt.
3. **Option Flows:** Richtung bullisch / neutral / bärisch aus `python3 tools/optionsfluesse.py <Ticker>` (öffentliche,
   verzögerte Cboe-Optionsdaten, nur US-Aktien). Eine **Näherung aus dem Tagesumsatz** (Put/Call im Vergleich zum
   Normalwert der Aktie, Prämien, ungewöhnliche Kontrakte), bewertet **auf Jahresbasis**: die heutige Lage wird mit den
   eigenen Tageswerten der Aktie der letzten bis zu 252 Handelstage verglichen (`tools/flows-sammeln.py` sammelt sie
   täglich; bis 40 Werte vorliegen, gilt eine Ersatzregel), kein echter Institutionen-Flow: wer kauft oder verkauft,
   sieht man dort nicht. Ohne Daten (z. B. Nicht-US-Aktie) steht „keine Daten“; geschätzt wird nichts.

Seine Einordnung ist reine Marktstruktur und Stimmung, **keine** Bewertung des Unternehmens. Typischer Widerspruch zu
Warren: Das Unternehmen kann gut und der Kurs trotzdem „Down“ sein. Dann sagt James das, auch wenn Warren gefällt.

## Setup-Score, RSI, MACD und Muster (eigene, offene Regeln, `tools/trend.py` und `tools/muster.py`)
Angelehnt an Chart-Scanner, wie James sie täglich zeigt (Punktestand aus leuchtenden Signalen), aber **kein Nachbau seines
Scores**: Seine Schwellen und Gewichte kennen wir nicht. Unser Score hat 12 Regeln, jede erfüllte zählt einen Punkt:
Trend (Kurs über 8, 21 und 50 geordnet; über der steigenden 200er; über dem 10-Wochen-EMA; höhere Hochs und Tiefs),
Stärke (höchstens 5 % unter dem 52-Wochen-Hoch; besser als der S&P 500 über 3 Monate), Momentum (RSI(14) 50–75; MACD über
der Signallinie), Volumen (Auf-/Abtage-Verhältnis über 1,1; On-Balance-Volume steigt), Spannung (Squeeze oder verengte ATR;
NR7 oder Umsatz-Dry-Up). Stufen: 0–3 Schwach, 4–5 Beobachten, 6–8 Momentum im Aufbau, 9–12 Stark.
RSI(14) nach Wilder, MACD (12, 26, 9). **Muster im 1-Jahres-Chart:** Unterstützungslinie aus höheren Tiefs, Widerstandslinie aus
tieferen Hochs, Bodenbildung (Doppelboden oder höheres Tief nach einem Rückgang von mindestens 15 %, mit Nackenlinie). Die
genauen Regeln stehen im Kopf von `tools/muster.py`. Das sind einfache Faustregeln, keine Prognose.

## Grenzen
- Die öffentlichen Seiten nennen die gleitenden Durchschnitte als Auslöser (ausdrücklich nur den 21er-EMA), aber nicht
  vollständig, welche genau er nutzt. Die Linien 8, 21, 50, 200 und die Zonen stammen von Thomas.
- James ist Händler (Tage bis Wochen), Warren und Charlie sind Halter (Jahre). Das ist gewollt: drei Zeithorizonte.
- Im Aktien-Check ist James eine KI-Figur nach seiner öffentlich beschriebenen Methode. Er hat die Einschätzungen
  nicht abgegeben und die Seite ist nicht mit ihm abgestimmt.
