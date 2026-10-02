/**
 * Aktien-Check – Eingang sofort abarbeiten lassen.
 *
 * Gehört in die Google-Tabelle „Aktien Eingang“ (Erweiterungen → Apps Script).
 * Bei jeder neuen Formular-Antwort wird die Claude-Routine „Aktien abarbeiten“ über ihren API-Auslöser gestartet.
 * Die Routine liest die Tabelle und arbeitet offene Einträge nach AKTIEN-ABLAUF.md ab.
 *
 * Einrichten (einmalig):
 *  1. ROUTINE_URL unten durch die URL des API-Auslösers der neuen Routine ersetzen.
 *  2. Projekteinstellungen (Zahnrad) → Skripteigenschaften → ROUTINE_TOKEN = Schlüssel des Auslösers (nicht in den Code!).
 *  3. Funktion `einrichten` ausführen (Berechtigungen erlauben), danach `testAusloesen`.
 */
var ROUTINE_URL = 'https://api.anthropic.com/v1/claude_code/routines/HIER_TRIGGER_ID/fire';
var ANTHROPIC_VERSION = '2023-06-01';
var ANTHROPIC_BETA = 'experimental-cc-routine-2026-04-01';
var MAX_LAEUFE_PRO_TAG = 15; // Sperre gegen Spam (Seite ist öffentlich)

function einrichten() {
  var ss = SpreadsheetApp.getActive();
  ScriptApp.getProjectTriggers().forEach(function (t) {
    if (t.getHandlerFunction() === 'beiNeuerAntwort') ScriptApp.deleteTrigger(t);
  });
  ScriptApp.newTrigger('beiNeuerAntwort').forSpreadsheet(ss).onFormSubmit().create();
}

function beiNeuerAntwort() {
  var props = PropertiesService.getScriptProperties();
  var heute = Utilities.formatDate(new Date(), 'Europe/Berlin', 'yyyy-MM-dd');
  var z = JSON.parse(props.getProperty('LAEUFE') || '{}');
  var n = z[heute] || 0;
  if (n >= MAX_LAEUFE_PRO_TAG) return; // Eintrag bleibt offen und wird beim nächsten Lauf miterledigt
  var neu = {}; neu[heute] = n + 1;
  props.setProperty('LAEUFE', JSON.stringify(neu));
  routineStarten('Neuer Eintrag im Aktien-Eingang.');
}

function testAusloesen() { routineStarten('Testaufruf aus Apps Script.'); }

function routineStarten(hinweis) {
  var token = PropertiesService.getScriptProperties().getProperty('ROUTINE_TOKEN');
  if (!token) throw new Error('Skripteigenschaft ROUTINE_TOKEN fehlt.');
  var cache = CacheService.getScriptCache();
  if (cache.get('laeuft')) return;
  var antwort = UrlFetchApp.fetch(ROUTINE_URL, {
    method: 'post',
    contentType: 'application/json',
    headers: { 'Authorization': 'Bearer ' + token, 'anthropic-version': ANTHROPIC_VERSION, 'anthropic-beta': ANTHROPIC_BETA },
    payload: JSON.stringify({ text: hinweis }),
    muteHttpExceptions: true
  });
  var code = antwort.getResponseCode();
  Logger.log('Routine: HTTP ' + code + ' ' + antwort.getContentText());
  if (code >= 200 && code < 300) cache.put('laeuft', '1', 120);
  else if (code === 400 || code === 409 || code === 429) nachholenPlanen();
  else throw new Error('Routine nicht gestartet: HTTP ' + code);
}

function nachholenPlanen() {
  var geplant = ScriptApp.getProjectTriggers().some(function (t) { return t.getHandlerFunction() === 'nachholen'; });
  if (!geplant) ScriptApp.newTrigger('nachholen').timeBased().after(10 * 60 * 1000).create();
}

function nachholen() {
  ScriptApp.getProjectTriggers().forEach(function (t) {
    if (t.getHandlerFunction() === 'nachholen') ScriptApp.deleteTrigger(t);
  });
  CacheService.getScriptCache().remove('laeuft');
  routineStarten('Nachhol-Start.');
}
