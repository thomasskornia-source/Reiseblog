/**
 * Reiseideen – Bewertungen von Thomas und Andrea sammeln.
 *
 * Einrichten (einmalig, ca. 3 Minuten):
 *  1. Neue Google-Tabelle anlegen (Name egal), darin Erweiterungen → Apps Script, diesen Code einfügen, speichern.
 *  2. Funktion `einrichten` einmal ausführen (Berechtigungen erlauben). Sie legt das Blatt „Stimmen“ an.
 *  3. Bereitstellen → Neue Bereitstellung → Typ „Web-App“: Ausführen als „Ich“, Zugriff „Jeder“. Die Web-App-URL (endet auf /exec) kopieren.
 *  4. Die URL in data/reiseideen-config.json bei "url" eintragen (oder Claude geben), danach sind die Bewertungen gemeinsam.
 *
 * Es gibt nur die Namen Thomas und Andrea, je Reise eine Stimme (1 bis 5 Sterne), eine neue Stimme ersetzt die alte.
 * Lesen: …/exec  →  {"<reise-id>": {"Thomas": 4, "Andrea": 5}, …}
 * Schreiben: …/exec?id=<reise-id>&name=Thomas&sterne=4   (sterne=0 nimmt die Stimme zurück)
 */
var NAMEN = ['Thomas', 'Andrea'];
var MAX_ZEILEN = 400;

function blatt() {
  var ss = SpreadsheetApp.getActive(), sh = ss.getSheetByName('Stimmen');
  if (!sh) { sh = ss.insertSheet('Stimmen'); sh.appendRow(['id', 'name', 'sterne', 'zeit']); }
  return sh;
}
function einrichten() { blatt(); }

function alle() {
  var v = blatt().getDataRange().getValues(), out = {};
  for (var i = 1; i < v.length; i++) {
    if (!v[i][0]) continue;
    (out[v[i][0]] = out[v[i][0]] || {})[v[i][1]] = Number(v[i][2]);
  }
  return out;
}

function doGet(e) {
  var p = (e && e.parameter) || {}, lock = LockService.getScriptLock();
  if (p.id && p.name) {
    var id = String(p.id).replace(/[^a-z0-9-]/gi, '').slice(0, 60), name = String(p.name), s = parseInt(p.sterne, 10);
    if (id && NAMEN.indexOf(name) >= 0 && s >= 0 && s <= 5) {
      lock.waitLock(10000);
      try {
        var sh = blatt(), v = sh.getDataRange().getValues(), zeile = 0;
        for (var i = 1; i < v.length; i++) if (v[i][0] === id && v[i][1] === name) { zeile = i + 1; break; }
        if (s === 0) { if (zeile) sh.deleteRow(zeile); }
        else if (zeile) sh.getRange(zeile, 3, 1, 2).setValues([[s, new Date()]]);
        else if (v.length < MAX_ZEILEN) sh.appendRow([id, name, s, new Date()]);
      } finally { lock.releaseLock(); }
    }
  }
  return ContentService.createTextOutput(JSON.stringify(alle())).setMimeType(ContentService.MimeType.JSON);
}
