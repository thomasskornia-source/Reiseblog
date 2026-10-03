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

## YouTube-Kanal (öffentlich sichtbar: Kanalbeschreibung und Titel der Videos, Stand 03.10.2026)
Quelle: https://www.youtube.com/@jamesbulltard (Videos selbst nicht angesehen, kein Zugriff auf Inhalte; keine Mitschriften, nur
Titel und Beschreibungen aus dem öffentlichen Kanal-Feed, in eigenen Worten).
- **Selbstbeschreibung des Kanals:** ungeschnittene Marktkommentare, „Technical Analysis Does Matter“, Ziel: Märkte
  verständlicher machen. Bildung laut Kanalseite: Mathematical Economic Analysis (BA) und Financial Engineering (SM).
  Der Name ist ein Online-Name; nicht zu verwechseln mit James Bullard, dem früheren Präsidenten der Fed-Filiale St. Louis.
- **Schwerpunkt (nach eigener Aussage):** **PEAD** (Post-Earnings-Announcement-Drift: Kurse laufen nach guten
  Quartalszahlen oft noch weiter in dieselbe Richtung) und das **Verkaufen von Optionsprämie in Stärke** (Put-Verkauf,
  wenn der Wert stark ist). Dazu tägliche Recaps und ungewöhnliche Optionsumsätze, das meiste hinter einer Bezahlschranke
  (Substack mit Datenbank, Scanner, Rankings und Discord-Community).
- **Typisches Videoformat (Juni 2026):** „Ticker, ein tieferer Blick auf die Aktie: Options Flow, Charts und Trade-Ideen“,
  jeweils zu einer großen Aktie (Intel, Amazon, Coupang, Fiserv, Deere, Zoetis, SpaceX …). Die Reihenfolge der Titel ist
  gleich: erst Options Flow, dann Charts, dann Trade-Ideen. Bei Insiderkäufen oder großen Optionskäufen („30-Mio.-Call“)
  werden diese als Auslöser genannt.
- **Weitere Themen:** der Blick auf einen eigenen Scanner und auf Charts; Einordnung von Marktschwäche (z. B. „Semi-Crash,
  nicht Markt-Crash“); große Risk Reversals und Optionsgeschäfte; Marktstimmung rund um Zahlen großer Konzerne.
- **Was wir daraus mitnehmen:** (1) Reihenfolge Flows → Chart → Idee bestätigt unsere Darstellung; (2) die Haltung
  „nicht gegen den Trend und nicht in schwache Werte“; (3) Hinweis auf Insiderkäufe und Zahlen als zusätzliche Auslöser
  (heute nicht in unseren Zahlen). Nicht übernommen: Renditeversprechen („höchste Konversion auf Substack“), Handelsideen,
  Aussagen über Dritte.

## Podcast-Interview „The Atomic Level“ (Substack, 2026; 67 Minuten, frei zugänglich)
Quelle: Podcast-Folge „The Faceless Trader Beating the Biggest Names in Finance“ (Gastgeber Chris Snook; James nur als Stimme, sein Gesicht
bleibt ein Avatar). Per Spracherkennung selbst transkribiert und **nur in eigenen Worten zusammengefasst**; die Mitschrift selbst liegt
nicht im Repo. Alles unten sind Selbstaussagen von James, nicht geprüft.
- **Grundhaltung:** Ein Chart sieht entweder gut aus oder nicht, er verschwendet keine Zeit. Auf lange Sicht gehe jede gute Aktie hoch;
  schwer sei der Zeitpunkt, und den zeige der Chart. Große Firmen seien nicht automatisch gute Käufe zu jedem Preis; **jede Aktie ist
  irgendwo auf dem Chart ein Kauf**, nur nicht überall. Er bleibt bei Aktien, kein Handel mit Anleihen oder Rohstoffen.
- **Warum gleitende Durchschnitte:** Der Großteil des Marktes sei Computerhandel, der keine Bilanzen liest, sondern feste Marken kauft und
  verkauft. Kurse bewegten sich tagsüber „aus Nichts“, aber Durchschnitte brechen. Wer kurzfristig handelt, müsse wie diese Computer denken.
- **Der 21-Tage-EMA ist die wichtigste Linie** (etwa ein Monat). Darüber: Risiko ausbauen („pressen“), nichts zu fürchten. Darunter:
  aufpassen. 90 % der Brüche darunter bleiben folgenlos, aber **jeder große Abverkauf begann mit einem Bruch unter dem 21er**. Seine Regel:
  unter der 21er kurzfristige Positionen verkleinern oder in Cash gehen; bei mehreren schlechten Tagen in Folge ist man im Abwärtstrend
  und fängt keine fallenden Messer. Er nutzt fünf Linien: **8-EMA und 21-EMA (kurzfristig), 50, 100 und 200 Tage (langfristig)**.
- **Nicht shorten:** Zuletzt 2018 geshortet. Es gebe zu oft künstliche Pumps oder Nachrichten. Statt Gegenwette: **warten, bis der Markt
  wieder über den Schlüssellinien steht**. Er hält ein Handelsbuch (wenige Positionen, Verlust verkraftbar) getrennt von langfristigen
  Anlagen, die er kaum anschaut.
- **Option Flows (seine Hauptquelle):** Alle Optionsdaten stammen von der Cboe; entscheidend sei der Filter. Er protokolliert von Hand
  rund 150 relevante Geschäfte pro Tag nach festen Regeln, eine KI baut aus der Datenbank Handelsideen. Wichtige Ideen:
  1. **Menge zählt, nicht ein einzelnes Geschäft:** Er zählt und rankt die Flows. Namen mit immer mehr Flow sind die, in denen man sein
     will; Namen im Abwärtstrend bekommen keine Call-Käufe. Große Bewegungen kämen selten ohne vorherige Optionsaktivität.
  2. **Große Put-Verkäufe zeigen, wo Großanleger kaufen wollen** (eine Einstiegsmarke nach Stunden Beratung im Fonds). Er baut daraus
     etwas darunter (z. B. 5 % tiefer) für sich. Selbstangabe: von rund 14.000 so markierten Put-Verkäufen seien 80 % wertlos verfallen.
  3. **13F-Meldungen sind zu spät** (Monate alt); Optionsflüsse zeigen, was jetzt passiert, auch Rotation zwischen Branchen (z. B. in
     einer Phase Öl und Dünger statt Chips).
- **Stil:** Kurz, offen, direkt, humorvoll („Bulltards“), warnt, wenn der Markt unter der 21er steht („was ihr hier tut, geht auf euch“),
  legt Einstiege und Ausstiege offen. Für Anfänger ist es nach eigener Aussage nicht gedacht, die meisten seiner Leser kennen sich aus.
  Zeithorizont: „die nächste 15-Minuten-Kerze“, nicht 90 Tage; er macht keine Prognosen über Monate.
- **Nicht übernommen:** seine Renditen, Positionen, Abozahlen und Umsätze (Eigenangaben, ungeprüft, Werbung), Aussagen über Politiker
  und andere Dritte, Marktprognosen.
- **Was daraus für unseren James folgt:** (1) Die 21er und das Verhältnis Kurs zu den Linien stehen im Vordergrund, wie bei uns.
  (2) Unter der 21er sagt James klar: keine neuen Käufe, abwarten, nicht gegen den Trend wetten und nicht shorten. (3) Flows nach
  Menge und Richtung bewerten, nicht einzelne Großgeschäfte. (4) Kurz, direkt, ohne Schnörkel: „Chart sieht gut aus“ oder nicht.
  (5) Unsere Linien enthalten die 100er nicht; wir lassen sie weg (50 und 200 reichen).

## Alte Newsletter-Mails von James (2023, aus Thomas' Postfach; nur sinngemäß, die Mails selbst liegen nicht im Repo)
Gelesen wurden zehn Mails aus dem Ordner „James“ (Tages-Recaps, „Best Idea For The Week Ahead“, „10 Charts Of Strength“, „How Do You Utilize
This Data?“, „The Process“, ein Zahlenausblick zu Amazon). Zusammenfassung in eigenen Worten; keine Handelsideen, Positionen, Gewinne
oder Rechnungs- und Kontodaten übernommen.
- **Aufbau seiner Tages-Recaps:** (1) kurze Marktlage mit Index-Chart (Tages- und Wochenchart, Lage zu den Linien, Divergenzen, gescheiterte
  Ausbrüche); (2) **„Trends“**: Ranking der Flows über Woche bis heute, 2 Wochen, 1 Monat, später auch 2 Monate (nur Geschäfte, deren
  Laufzeit noch offen ist); (3) **ungewöhnliche Optionsaktivität** des Tages mit Zahl der Geschäfte (rund 90 bis 110) und was auffiel;
  (4) eigene Positionen und was er getan hat; freitags (Verfallstag) nur eine kurze Fassung. Am Wochenende eine „beste Idee“ und
  „Charts der Stärke“ mit den zugehörigen Flows.
- **Seine Prozess-Reihenfolge** (Gliederung von „The Process“): Option Flows → Trends (was suche ich, Ideen, Timing, Richtung) → Charts
  (welche Durchschnitte, welche Zeitrahmen, warum) → Umsetzung (welche Optionen, wie einsteigen).
- **Der Sinn der „Trends“:** Namen, die über längere Zeit wiederholt bullische Flows sehen, sind die, in denen man sein will; Namen mit
  bärischen Flows meidet er. Gedacht, um Stärke und Schwäche zu erkennen: Puts in Stärke verkaufen, Schwäche meiden. Seine Leser nutzen
  dieselben Daten unterschiedlich (Aktien, Calls, Put-Verkauf je nach Kontogröße); es gebe nicht die eine richtige Methode.
- **Denkregeln und Sätze, die sich wiederholen:**
  - Der Markt irrt nie, nur die Teilnehmer; Charts sagen die Wahrheit „ohne eingebaute Geschichte“.
  - Der Optionsmarkt läuft Nachrichten voraus (viele weit entfernte Calls vor einer Meldung); darum schaut er zuerst auf Flows, weniger auf
    Fundamentaldaten. Makro sei schwer zu deuten, Kursverlauf und Flows nicht.
  - Im Aufwärtstrend ist jeder kleine Rücksetzer eine Kaufgelegenheit; wer dagegen shortet, „kämpft gegen die Schwerkraft“. Davor
    beobachtet er: viele lange Kerzendochte nach unten (Dips werden gekauft), RSI noch nicht überkauft, Ausbruch über Marken, die ein
    Jahr lang hielten.
  - **Marktbreite:** Er zählt, wie viele Großwerte über dem 8-EMA liegen. Sind es nur wenige, sind die „Innereien“ schwach, auch wenn der
    Index oben steht. Ist der Index unter dem 8-EMA, aber eine bullische Divergenz baut sich auf, heißt es: abwarten, bis der Kurs
    eindeutig ist, solange gilt der Aufwärtstrend.
  - **Nach einem Abverkauf** zählen Aktien, die den **8-EMA im Wochenchart** halten: Sie zeigen relative Stärke.
  - **Golden Cross** (50 kreuzt über 200) führe „typischerweise zu einem längeren Lauf“; wichtig auch Marken, an denen der Kurs im letzten
    Jahr mehrfach abgewiesen wurde (Ausbruch darüber).
  - „Je länger die Basis, desto höher der Raum“: lange Seitwärtsphasen vor Ausbrüchen.
  - Warnzeichen: unter der 200er brechende Branchenindizes zusammen mit vielen Put-Käufen (Beispiel Regionalbanken); Übertreibung bei
    heißen Neuemissionen („viel Schaum“); sehr niedrige Angst (VIX unter 15), während niemand Absicherung kauft.
  - Kalender: Zahlen, Notenbank-Treffen, Verfallstage nennt er als Auslöser, die Kurs und Flow bewegen.
  - **Gewinne mitnehmen:** Wer in einer Woche stark im Plus ist, soll nicht gierig werden; „es kommt immer der nächste Trade“. Er sagt auch
    offen, wenn ein Erfolg Glück war.
- **Stil in den Mails:** persönlich („ich“), direkt, mit klarer Meinung auch gegen große Firmen und Manager (z. B. zu hohen Investitionen),
  Zahlen und Chartbilder als Belege, kurze Absätze, Humor, einladend zur Community („wie nutzt ihr die Daten?“). Er schreibt von sich,
  dass er über 20 Jahre handelt und fast drei Jahrzehnte gebraucht habe, seine Methode zu verfeinern.
- **Was daraus für unseren James folgt (Vorschläge):** (1) **Marktbreite** als eigener Wert ergänzen: Anteil der S&P-500-Aktien über 8-,
  21-, 50- und 200-Tage-Linie, täglich aus unserer eigenen Berechnung (kostenlos). (2) Als Stärke-Regel den **Wochen-8-EMA** ansehen
  (heute zählt der 10-Wochen-EMA im Score). (3) Golden Cross und Marken, an denen der Kurs im letzten Jahr mehrfach abprallte, sind
  schon bzw. teilweise drin. (4) Flow-Ranking über mehrere Zeiträume bräuchte ein tägliches Sammeln der Optionsdaten für viele Aktien;
  unsere frei verfügbare Cboe-Näherung reicht dafür nur eingeschränkt.

## Grenzen
- Die öffentlichen Seiten nennen die gleitenden Durchschnitte als Auslöser (ausdrücklich nur den 21er-EMA), aber nicht
  vollständig, welche genau er nutzt. Die Linien 8, 21, 50, 200 und die Zonen stammen von Thomas.
- James ist Händler (Tage bis Wochen), Warren und Charlie sind Halter (Jahre). Das ist gewollt: drei Zeithorizonte.
- Im Aktien-Check ist James eine KI-Figur nach seiner öffentlich beschriebenen Methode. Er hat die Einschätzungen
  nicht abgegeben und die Seite ist nicht mit ihm abgestimmt.
